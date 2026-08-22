"""Native Gmsh API owned by the persistent GUI main thread."""

import array
import hashlib
import math
import os

from integrations.common.errors import BridgeError, INVALID_PARAMS, METHOD_NOT_FOUND
from integrations.common.session import SessionCoordinator
from . import BRIDGE_VERSION, PROTOCOL_VERSION
from .contract import METHOD_SPECS, SPEC_BY_NAME


MESH_OPTIONS = {
    "Mesh.MeshSizeMin",
    "Mesh.MeshSizeMax",
    "Mesh.ElementOrder",
    "Mesh.SecondOrderLinear",
    "Mesh.Algorithm",
    "Mesh.Algorithm3D",
    "Mesh.Optimize",
    "Mesh.OptimizeNetgen",
    "Mesh.SaveAll",
    "Mesh.SurfaceEdges",
    "Mesh.SurfaceFaces",
    "Mesh.VolumeEdges",
    "Mesh.VolumeFaces",
}
QUALITY_NAMES = {"minSICN", "minSIGE", "minSJ", "gamma", "minDetJac"}


class GmshAPI:
    def __init__(self, gmsh_module, path_policy, socket_path, gui):
        self.gmsh = gmsh_module
        self.path_policy = path_policy
        self.socket_path = socket_path
        self.gui = bool(gui)
        self.session = SessionCoordinator("gmsh")

    def dispatch(self, method, params):
        if method not in SPEC_BY_NAME:
            raise BridgeError(METHOD_NOT_FOUND, "Unknown Gmsh method", {"method": method})
        handler = getattr(self, "_" + method.replace(".", "_"))
        return handler(params)

    def _system_ping(self, params):
        self._empty(params)
        return {
            "bridge_version": BRIDGE_VERSION,
            "protocol_version": PROTOCOL_VERSION,
            "gmsh_version": getattr(self.gmsh, "__version__", "unknown"),
            "socket": self.socket_path,
            "pid": os.getpid(),
            "gui": self.gui and bool(self.gmsh.fltk.isAvailable()),
            "interaction_level": "native-cooperative",
            "model": self.gmsh.model.getCurrent(),
            "session": self.session.snapshot(),
        }

    def _system_capabilities(self, params):
        self._empty(params)
        return {
            "application": "gmsh",
            "interaction_level": "native-cooperative",
            "methods": [spec.as_dict() for spec in METHOD_SPECS],
        }

    def _session_observe(self, params):
        self._empty(params)
        return self.session.observe(self._state())

    def _session_acquire(self, params):
        self._require(params, "actor", "expected_revision")
        return self.session.acquire(
            params["actor"], params["expected_revision"], params.get("ttl_seconds", 300)
        )

    def _session_release(self, params):
        self._require(params, "actor")
        return self.session.release(params["actor"])

    def _session_history(self, params):
        return {"steps": self.session.recent_history(params.get("limit", 20))}

    def _model_open(self, params):
        self._mutation_fields(params, "path")
        path = self.path_policy.resolve_read(params["path"])
        return self._mutate(params, "model.open", lambda: self._open(path))

    def _model_clear(self, params):
        self._mutation_fields(params)
        return self._mutate(params, "model.clear", self._clear)

    def _model_entities(self, params):
        dim = self._dimension(params.get("dimension", -1), allow_all=True)
        observation = self.session.observe(self._state())
        return {"session": observation, "entities": self._entities(dim)}

    def _model_entities_in_bbox(self, params):
        self._require(params, "minimum", "maximum")
        minimum = self._vector3(params["minimum"], "minimum")
        maximum = self._vector3(params["maximum"], "maximum")
        if any(a > b for a, b in zip(minimum, maximum)):
            raise BridgeError(INVALID_PARAMS, "minimum must not exceed maximum")
        dim = self._dimension(params.get("dimension", -1), allow_all=True)
        entities = self.gmsh.model.getEntitiesInBoundingBox(*minimum, *maximum, dim)
        return {
            "session": self.session.observe(self._state()),
            "entities": [{"dimension": int(d), "tag": int(t)} for d, t in entities],
        }

    def _mesh_configure(self, params):
        self._mutation_fields(params, "options")
        options = params["options"]
        if not isinstance(options, dict) or not options:
            raise BridgeError(INVALID_PARAMS, "options must be a non-empty object")
        unknown = sorted(set(options) - MESH_OPTIONS)
        if unknown:
            raise BridgeError(INVALID_PARAMS, "Mesh option is not allowlisted", {"options": unknown})

        def action():
            changed = {}
            for name, value in options.items():
                if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                    raise BridgeError(INVALID_PARAMS, "Mesh option values must be finite numbers")
                old = self.gmsh.option.getNumber(name)
                self.gmsh.option.setNumber(name, float(value))
                changed[name] = {"old": old, "new": self.gmsh.option.getNumber(name)}
            self._refresh()
            return {"options": changed}

        return self._mutate(params, "mesh.configure", action)

    def _mesh_generate(self, params):
        self._mutation_fields(params, "dimension")
        dimension = self._dimension(params["dimension"])

        def action():
            self.gmsh.logger.start()
            try:
                self.gmsh.model.mesh.generate(dimension)
                messages = list(self.gmsh.logger.get())
            finally:
                self.gmsh.logger.stop()
            self._refresh()
            return {"dimension": dimension, "messages": messages, "statistics": self._mesh_stats()}

        return self._mutate(params, "mesh.generate", action)

    def _mesh_clear(self, params):
        self._mutation_fields(params)

        def action():
            self.gmsh.model.mesh.clear()
            self._refresh()
            return {"cleared": True}

        return self._mutate(params, "mesh.clear", action)

    def _mesh_statistics(self, params):
        quality = params.get("quality_name", "minSICN")
        if quality not in QUALITY_NAMES:
            raise BridgeError(INVALID_PARAMS, "Unknown quality measure", {"allowed": sorted(QUALITY_NAMES)})
        return {
            "session": self.session.observe(self._state()),
            "statistics": self._mesh_stats(quality),
        }

    def _mesh_write(self, params):
        self._mutation_fields(params, "path")
        path = self.path_policy.resolve_write(params["path"])

        def action():
            self.gmsh.write(str(path))
            return {"artifact": self._artifact(path)}

        return self._mutate(params, "mesh.write", action)

    def _groups_create(self, params):
        self._mutation_fields(params, "dimension", "entity_tags", "name")
        dimension = self._dimension(params["dimension"])
        tags = params["entity_tags"]
        if not isinstance(tags, list) or not tags or not all(isinstance(tag, int) for tag in tags):
            raise BridgeError(INVALID_PARAMS, "entity_tags must be a non-empty integer array")
        name = params["name"]
        if not isinstance(name, str) or not name:
            raise BridgeError(INVALID_PARAMS, "name must be a non-empty string")

        def action():
            tag = self.gmsh.model.addPhysicalGroup(dimension, tags, int(params.get("tag", -1)), name)
            self._refresh()
            return {"dimension": dimension, "tag": int(tag), "name": name, "entity_tags": tags}

        return self._mutate(params, "groups.create", action)

    def _groups_list(self, params):
        self._empty(params)
        return {"session": self.session.observe(self._state()), "groups": self._physical_groups()}

    def _gui_update(self, params):
        self._empty(params)
        self._refresh()
        return {"updated": True, "session": self.session.observe(self._state())}

    def _gui_select_entities(self, params):
        self._mutation_fields(params)
        if not self.gui:
            raise BridgeError(INVALID_PARAMS, "GUI entity selection is unavailable in headless mode")
        dimension = self._dimension(params.get("dimension", -1), allow_all=True)

        def action():
            status, entities = self.gmsh.fltk.selectEntities(dimension)
            return {
                "selection_status": int(status),
                "entities": [{"dimension": int(d), "tag": int(t)} for d, t in entities],
            }

        return self._mutate(params, "gui.select_entities", action)

    def _gui_save_screenshot(self, params):
        self._mutation_fields(params, "path")
        if not self.gui:
            raise BridgeError(INVALID_PARAMS, "GUI screenshot is unavailable in headless mode")
        path = self.path_policy.resolve_write(params["path"])

        def action():
            self.gmsh.write(str(path))
            return {"artifact": self._artifact(path)}

        return self._mutate(params, "gui.save_screenshot", action)

    def _mutate(self, params, operation, action):
        public_arguments = {k: v for k, v in params.items() if k not in ("actor", "expected_revision")}
        return self.session.run_action(
            params["actor"],
            params["expected_revision"],
            operation,
            public_arguments,
            self._state,
            action,
        )

    def _open(self, path):
        self.gmsh.open(str(path))
        self._refresh()
        return {"path": str(path), "model": self.gmsh.model.getCurrent(), "entities": self._entities(-1)}

    def _clear(self):
        self.gmsh.clear()
        self._refresh()
        return {"cleared": True, "model": self.gmsh.model.getCurrent()}

    def _refresh(self):
        if self.gui:
            self.gmsh.fltk.update()
            self.gmsh.graphics.draw()

    def _state(self):
        entities = self._entities(-1)
        mesh = self._mesh_counts()
        mesh_options = {
            name: float(self.gmsh.option.getNumber(name))
            for name in sorted(MESH_OPTIONS)
        }
        node_tags, coordinates, _ = self.gmsh.model.mesh.getNodes()
        coordinate_bytes = (
            coordinates.tobytes()
            if hasattr(coordinates, "tobytes")
            else array.array("d", coordinates).tobytes()
        )
        fingerprint = hashlib.sha256()
        fingerprint.update(repr(entities).encode("utf-8"))
        fingerprint.update(repr(mesh).encode("utf-8"))
        fingerprint.update(repr(mesh_options).encode("utf-8"))
        fingerprint.update(repr(self._physical_groups()).encode("utf-8"))
        fingerprint.update(coordinate_bytes)
        return {
            "model": self.gmsh.model.getCurrent(),
            "file": self.gmsh.model.getFileName(),
            "entity_counts": {str(dim): len(self.gmsh.model.getEntities(dim)) for dim in range(4)},
            "mesh": mesh,
            "mesh_options": mesh_options,
            "physical_groups": self._physical_groups(),
            "native_fingerprint": fingerprint.hexdigest(),
        }

    def _entities(self, dimension):
        result = []
        for dim, tag in self.gmsh.model.getEntities(dimension):
            bbox = self.gmsh.model.getBoundingBox(dim, tag)
            result.append(
                {
                    "dimension": int(dim),
                    "tag": int(tag),
                    "bounding_box": [float(value) for value in bbox],
                }
            )
        return result

    def _physical_groups(self):
        result = []
        for dim, tag in self.gmsh.model.getPhysicalGroups():
            result.append(
                {
                    "dimension": int(dim),
                    "tag": int(tag),
                    "name": self.gmsh.model.getPhysicalName(dim, tag),
                    "entity_tags": [int(value) for value in self.gmsh.model.getEntitiesForPhysicalGroup(dim, tag)],
                }
            )
        return result

    def _mesh_counts(self):
        node_tags, _, _ = self.gmsh.model.mesh.getNodes()
        by_dimension = {}
        total = 0
        for dimension in range(4):
            _, element_tags, _ = self.gmsh.model.mesh.getElements(dimension)
            count = sum(len(tags) for tags in element_tags)
            by_dimension[str(dimension)] = count
            total += count
        return {"nodes": len(node_tags), "elements": total, "elements_by_dimension": by_dimension}

    def _mesh_stats(self, quality_name="minSICN"):
        counts = self._mesh_counts()
        _, groups, _ = self.gmsh.model.mesh.getElements(3)
        tags = [int(tag) for group in groups for tag in group]
        quality = list(self.gmsh.model.mesh.getElementQualities(tags, quality_name)) if tags else []
        counts["volume_elements"] = len(tags)
        counts["quality"] = {
            "name": quality_name,
            "minimum": min(quality) if quality else None,
            "maximum": max(quality) if quality else None,
            "mean": sum(quality) / len(quality) if quality else None,
            "below_0_1": sum(value < 0.1 for value in quality),
            "below_0_3": sum(value < 0.3 for value in quality),
        }
        return counts

    @staticmethod
    def _artifact(path):
        digest = hashlib.sha256()
        with open(path, "rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return {"path": str(path), "bytes": path.stat().st_size, "sha256": digest.hexdigest()}

    @staticmethod
    def _dimension(value, allow_all=False):
        allowed = {-1, 0, 1, 2, 3} if allow_all else {0, 1, 2, 3}
        if not isinstance(value, int) or value not in allowed:
            raise BridgeError(INVALID_PARAMS, "Invalid entity dimension", {"allowed": sorted(allowed)})
        return value

    @staticmethod
    def _vector3(value, name):
        if not isinstance(value, list) or len(value) != 3 or not all(isinstance(v, (int, float)) for v in value):
            raise BridgeError(INVALID_PARAMS, "{} must be three numbers".format(name))
        return [float(v) for v in value]

    @staticmethod
    def _empty(params):
        if params:
            raise BridgeError(INVALID_PARAMS, "This method takes no parameters")

    @staticmethod
    def _require(params, *names):
        missing = [name for name in names if name not in params]
        if missing:
            raise BridgeError(INVALID_PARAMS, "Missing required parameters", {"missing": missing})

    def _mutation_fields(self, params, *extra):
        self._require(params, "actor", "expected_revision", *extra)
