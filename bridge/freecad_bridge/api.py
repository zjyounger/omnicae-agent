"""Allowlisted FreeCAD App and Gui operations."""

import contextlib
import math
import os
import re

import FreeCAD as App
import FreeCADGui as Gui
import Import

from .errors import BridgeError, INVALID_PARAMS, METHOD_NOT_FOUND, invalid_params
from .contract import BRIDGE_PROTOCOL_VERSION, BRIDGE_VERSION, CONTRACT_VERSION, METHOD_SPECS


PROTOCOL_VERSION = BRIDGE_PROTOCOL_VERSION
_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# kind -> (FreeCAD type id, ((parameter, property, sign), ...))
PRIMITIVES = {
    "box": (
        "Part::Box",
        (("length", "Length", "positive"), ("width", "Width", "positive"), ("height", "Height", "positive")),
    ),
    "sphere": ("Part::Sphere", (("radius", "Radius", "positive"),)),
    "cylinder": (
        "Part::Cylinder",
        (("radius", "Radius", "positive"), ("height", "Height", "positive")),
    ),
    "cone": (
        "Part::Cone",
        (
            ("radius1", "Radius1", "non_negative"),
            ("radius2", "Radius2", "non_negative"),
            ("height", "Height", "positive"),
        ),
    ),
    "torus": (
        "Part::Torus",
        (("radius1", "Radius1", "positive"), ("radius2", "Radius2", "positive")),
    ),
}

BOOLEAN_OPERATIONS = {
    "cut": "Part::Cut",
    "fuse": "Part::MultiFuse",
    "common": "Part::MultiCommon",
}

# Property type ids the generic property API can read and write safely.
_PROPERTY_KINDS = {
    "App::PropertyFloat": "float",
    "App::PropertyFloatConstraint": "float",
    "App::PropertyPrecision": "float",
    "App::PropertyQuantity": "float",
    "App::PropertyQuantityConstraint": "float",
    "App::PropertyLength": "float",
    "App::PropertyDistance": "float",
    "App::PropertyArea": "float",
    "App::PropertyVolume": "float",
    "App::PropertyAngle": "float",
    "App::PropertyInteger": "int",
    "App::PropertyIntegerConstraint": "int",
    "App::PropertyPercent": "int",
    "App::PropertyBool": "bool",
    "App::PropertyString": "str",
    "App::PropertyEnumeration": "enum",
    "App::PropertyVector": "vector",
    "App::PropertyVectorDistance": "vector",
    "App::PropertyPosition": "vector",
    "App::PropertyDirection": "vector",
    "App::PropertyPlacement": "placement",
    # Link types are what FEM constraints use to point at geometry, so the
    # generic property API has to cover them or every constraint would need a
    # dedicated method.
    "App::PropertyLink": "link",
    "App::PropertyLinkList": "link_list",
    "App::PropertyLinkSub": "link_sub",
    "App::PropertyLinkSubList": "link_sub_list",
    "App::PropertyMap": "map",
    "App::PropertyStringList": "string_list",
}

# Domain object factories exposed as one generic method. FEM objects are Python
# features: a bare addObject() produces an object without its Proxy, which then
# silently fails to write anything to the solver deck.
FEM_KINDS = {
    "analysis": "makeAnalysis",
    "solver_ccx": "makeSolverCalculiXCcxTools",
    "material_solid": "makeMaterialSolid",
    "mesh_gmsh": "makeMeshGmsh",
    "mesh_region": "makeMeshRegion",
    "mesh_group": "makeMeshGroup",
    "constraint_fixed": "makeConstraintFixed",
    "constraint_displacement": "makeConstraintDisplacement",
    "constraint_force": "makeConstraintForce",
    "constraint_pressure": "makeConstraintPressure",
    "constraint_contact": "makeConstraintContact",
    "constraint_tie": "makeConstraintTie",
    "constraint_spring": "makeConstraintSpring",
    "constraint_selfweight": "makeConstraintSelfWeight",
    "constraint_sectionprint": "makeConstraintSectionPrint",
    "constraint_transform": "makeConstraintTransform",
    "constraint_rigidbody": "makeConstraintRigidBody",
}


_VIEW_PREFERENCES = "User parameter:BaseApp/Preferences/View"


@contextlib.contextmanager
def _without_navigation_animation():
    """Suppress FreeCAD's camera animation for one programmatic view change.

    The animation duration scales with camera travel and blocks the calling
    thread, which made gui.fit_all take 11 s on a 20-face model. Nobody is
    watching a Bridge-driven camera move, and the user's own interactive
    setting is restored afterwards.
    """
    preferences = App.ParamGet(_VIEW_PREFERENCES)
    was_set = "UseNavigationAnimations" in preferences.GetBools()
    previous = preferences.GetBool("UseNavigationAnimations", True)
    preferences.SetBool("UseNavigationAnimations", False)
    try:
        yield
    finally:
        if was_set:
            preferences.SetBool("UseNavigationAnimations", previous)
        else:
            preferences.RemBool("UseNavigationAnimations")


def _vector(value):
    return [float(value.x), float(value.y), float(value.z)]


def _finite_number(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise invalid_params("Expected a number", field, value)
    value = float(value)
    if not math.isfinite(value):
        raise invalid_params("Expected a finite number", field, value)
    return value


def _signed_number(value, field, sign):
    value = _finite_number(value, field)
    if sign == "positive" and value <= 0:
        raise invalid_params("Expected a positive number", field, value)
    if sign == "non_negative" and value < 0:
        raise invalid_params("Expected a non-negative number", field, value)
    return value


def _vector_value(value, field):
    if not isinstance(value, list) or len(value) != 3:
        raise invalid_params("Expected a three-item list", field, value)
    return [_finite_number(item, field) for item in value]


def _rotation(value, field="rotation"):
    """Build an App.Rotation from an axis-angle object, or identity when omitted."""
    if value is None:
        return App.Rotation()
    if not isinstance(value, dict):
        raise invalid_params("Rotation must be an object", field, value)
    unknown = set(value) - {"axis", "angle"}
    if unknown:
        raise invalid_params("Unknown rotation fields", field, sorted(unknown))
    axis = _vector_value(value.get("axis", [0.0, 0.0, 1.0]), field + ".axis")
    if all(item == 0.0 for item in axis):
        raise invalid_params("Rotation axis must not be the zero vector", field + ".axis", axis)
    angle = _finite_number(value.get("angle"), field + ".angle")
    return App.Rotation(App.Vector(*axis), angle)


def _name(value, field="name"):
    if not isinstance(value, str) or not _NAME_PATTERN.fullmatch(value):
        raise invalid_params(
            "Name must start with a letter or underscore and contain only letters, digits, and underscores",
            field,
            value,
        )
    return value


class FreeCADAPI:
    def __init__(self, path_policy, socket_path):
        self.path_policy = path_policy
        self.socket_path = socket_path
        self.methods = {
            "system.ping": self.system_ping,
            "system.capabilities": self.system_capabilities,
            "system.reload": self.system_reload,
            "documents.list": self.documents_list,
            "documents.new": self.documents_new,
            "documents.activate": self.documents_activate,
            "documents.open": self.documents_open,
            "documents.save": self.documents_save,
            "documents.close": self.documents_close,
            "objects.create": self.objects_create,
            "objects.list": self.objects_list,
            "objects.delete": self.objects_delete,
            "objects.get_properties": self.objects_get_properties,
            "objects.set_properties": self.objects_set_properties,
            "objects.transform": self.objects_transform,
            "objects.boolean": self.objects_boolean,
            "objects.inspect": self.cad_inspect_object,
            "shapes.list_faces": self.cad_list_faces,
            "shapes.find_planar_faces": self.cad_find_planar_faces,
            "cad.create_box": self.cad_create_box,
            "cad.inspect_object": self.cad_inspect_object,
            "cad.list_faces": self.cad_list_faces,
            "cad.find_planar_faces": self.cad_find_planar_faces,
            "fem.create": self.fem_create,
            "fem.mesh": self.fem_mesh,
            "fem.solve": self.fem_solve,
            "io.import_step": self.io_import_step,
            "io.export_step": self.io_export_step,
            "gui.activate_workbench": self.gui_activate_workbench,
            "gui.set_view": self.gui_set_view,
            "gui.fit_all": self.gui_fit_all,
            "gui.save_screenshot": self.gui_save_screenshot,
        }
        registered = {spec.name for spec in METHOD_SPECS}
        if set(self.methods) != registered:
            raise RuntimeError("Bridge method handlers and contract are out of sync")

    def dispatch(self, method, params):
        handler = self.methods.get(method)
        if handler is None:
            raise BridgeError(METHOD_NOT_FOUND, "Method not found", {"method": method})
        return handler(params)

    def _document(self, params, required=True):
        name = params.get("document")
        if name is None:
            doc = App.ActiveDocument
        else:
            if not isinstance(name, str):
                raise invalid_params("Document name must be a string", "document", name)
            doc = App.getDocument(name) if name in App.listDocuments() else None
        if doc is None and required:
            raise BridgeError(INVALID_PARAMS, "Document not found", {"document": name})
        return doc

    def _object(self, params):
        doc = self._document(params)
        name = params.get("object")
        if not isinstance(name, str) or not name:
            raise invalid_params("Object name must be a non-empty string", "object", name)
        obj = doc.getObject(name)
        if obj is None:
            raise BridgeError(
                INVALID_PARAMS,
                "Object not found",
                {"document": doc.Name, "object": name},
            )
        return doc, obj

    @staticmethod
    def _new_name(doc, params):
        name = _name(params.get("name"), "name")
        if doc.getObject(name) is not None:
            raise BridgeError(
                INVALID_PARAMS, "Object already exists", {"document": doc.Name, "object": name}
            )
        label = params.get("label")
        if label is None:
            label = name
        if not isinstance(label, str):
            raise invalid_params("Label must be a string", "label", label)
        return name, label

    @staticmethod
    def _property_kind(obj, name):
        try:
            type_id = obj.getTypeIdOfProperty(name)
        except Exception:
            return None, None
        kind = _PROPERTY_KINDS.get(type_id)
        if kind is None and type_id.startswith("App::Property"):
            # FreeCAD has dozens of unit-carrying properties (Force, Pressure,
            # Density, ThermalConductivity, ...). They all behave like a float
            # with a unit, so detect them instead of enumerating them.
            value = getattr(obj, name, None)
            if hasattr(value, "Value") and hasattr(value, "Unit"):
                kind = "float"
        return kind, type_id

    @staticmethod
    def _read_property(obj, name, kind):
        value = getattr(obj, name)
        if kind == "float":
            return float(getattr(value, "Value", value))
        if kind == "int":
            return int(value)
        if kind == "bool":
            return bool(value)
        if kind in ("str", "enum"):
            return str(value)
        if kind == "vector":
            return _vector(value)
        if kind == "link":
            return value.Name if value is not None else None
        if kind == "link_list":
            return [item.Name for item in value]
        if kind == "link_sub":
            if value is None or value[0] is None:
                return None
            return {"object": value[0].Name, "sub": list(value[1])}
        if kind == "link_sub_list":
            return [
                {"object": item[0].Name, "sub": list(item[1]) if item[1] else []}
                for item in value
            ]
        if kind == "map":
            return {str(k): str(v) for k, v in dict(value).items()}
        if kind == "string_list":
            return [str(item) for item in value]
        return {
            "position": _vector(value.Base),
            "rotation": {
                "axis": _vector(value.Rotation.Axis),
                "angle": math.degrees(float(value.Rotation.Angle)),
            },
        }

    @staticmethod
    def _link_target(document, value, field):
        if not isinstance(value, str) or not value:
            raise invalid_params("Expected an object name", field, value)
        target = document.getObject(value)
        if target is None:
            raise BridgeError(
                INVALID_PARAMS, "Object not found", {"document": document.Name, "object": value}
            )
        return target

    @classmethod
    def _link_sub(cls, document, value, field):
        if not isinstance(value, dict):
            raise invalid_params(
                "Expected {object, sub} with sub a list of subelement names", field, value
            )
        unknown = set(value) - {"object", "sub"}
        if unknown:
            raise invalid_params("Unknown link fields", field, sorted(unknown))
        target = cls._link_target(document, value.get("object"), field + ".object")
        subs = value.get("sub", [])
        if not isinstance(subs, list) or not all(isinstance(item, str) and item for item in subs):
            raise invalid_params("Sub must be a list of subelement names", field + ".sub", subs)
        return target, subs

    @staticmethod
    def _coerce_property(obj, name, kind, value):
        field = "values.{}".format(name)
        if kind == "float":
            # A bare number is written in FreeCAD's internal units, which for
            # anything but a length is rarely what the caller means: force is
            # kg*mm/s^2, so 5000 is 5 N, not 5000 N. Accept "5000 N" so the unit
            # can be stated explicitly and checked by FreeCAD.
            if isinstance(value, str):
                try:
                    return App.Units.Quantity(value)
                except Exception as exc:
                    raise invalid_params(
                        "Not a valid quantity, expected something like '5000 N'",
                        field,
                        {"value": value, "detail": str(exc)},
                    )
            return _finite_number(value, field)
        if kind == "int":
            if isinstance(value, bool) or not isinstance(value, int):
                raise invalid_params("Expected an integer", field, value)
            return value
        if kind == "bool":
            if not isinstance(value, bool):
                raise invalid_params("Expected a boolean", field, value)
            return value
        if kind == "str":
            if not isinstance(value, str):
                raise invalid_params("Expected a string", field, value)
            return value
        if kind == "enum":
            options = list(obj.getEnumerationsOfProperty(name))
            if value not in options:
                raise invalid_params(
                    "Value is not one of the allowed options", field, {"value": value, "options": options}
                )
            return value
        if kind == "vector":
            return App.Vector(*_vector_value(value, field))
        if kind in ("link", "link_list", "link_sub", "link_sub_list"):
            document = obj.Document
            if kind == "link":
                return None if value is None else FreeCADAPI._link_target(document, value, field)
            if kind == "link_list":
                if not isinstance(value, list):
                    raise invalid_params("Expected a list of object names", field, value)
                return [FreeCADAPI._link_target(document, item, field) for item in value]
            if kind == "link_sub":
                if value is None:
                    return None
                target, subs = FreeCADAPI._link_sub(document, value, field)
                return (target, subs)
            if not isinstance(value, list):
                raise invalid_params("Expected a list of {object, sub} entries", field, value)
            return [FreeCADAPI._link_sub(document, item, field) for item in value]
        if kind == "map":
            if not isinstance(value, dict) or not all(
                isinstance(k, str) and isinstance(v, str) for k, v in value.items()
            ):
                raise invalid_params("Expected an object of string values", field, value)
            return dict(value)
        if kind == "string_list":
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                raise invalid_params("Expected a list of strings", field, value)
            return list(value)
        if not isinstance(value, dict):
            raise invalid_params("Placement must be an object", field, value)
        unknown = set(value) - {"position", "rotation"}
        if unknown:
            raise invalid_params("Unknown placement fields", field, sorted(unknown))
        position = _vector_value(value.get("position", [0.0, 0.0, 0.0]), field + ".position")
        return App.Placement(
            App.Vector(*position), _rotation(value.get("rotation"), field + ".rotation")
        )

    @staticmethod
    def _document_info(doc):
        return {
            "name": doc.Name,
            "label": doc.Label,
            "file_name": doc.FileName or None,
            "object_count": len(doc.Objects),
            "active": App.ActiveDocument is doc,
        }

    def system_ping(self, params):
        del params
        version = App.Version()
        return {
            "bridge_version": BRIDGE_VERSION,
            "protocol_version": PROTOCOL_VERSION,
            "freecad_version": ".".join(str(item) for item in version[:3]),
            "pid": os.getpid(),
            "gui": True,
            "socket": self.socket_path,
            "active_document": App.ActiveDocument.Name if App.ActiveDocument else None,
        }

    def system_reload(self, params):
        del params
        # Scheduled rather than immediate: this request is being served by the
        # very server the reload replaces, so the reply has to go out and the
        # dispatch stack unwind first.
        import freecad_bridge

        freecad_bridge.schedule_reload()
        return {
            "scheduled": True,
            "version_before": BRIDGE_VERSION,
            "socket": self.socket_path,
            "note": "Reconnect shortly and call system.ping to see the reloaded version. "
            "If the new code fails to import, the current Bridge keeps serving.",
        }

    def system_capabilities(self, params):
        del params
        return {
            "bridge_version": BRIDGE_VERSION,
            "protocol_version": PROTOCOL_VERSION,
            "contract_version": CONTRACT_VERSION,
            "methods": sorted(self.methods),
            "method_specs": [spec.as_capability() for spec in METHOD_SPECS],
            "allowed_roots": self.path_policy.describe(),
            "arbitrary_python": False,
            "arbitrary_shell": False,
        }

    def documents_list(self, params):
        del params
        return {"documents": [self._document_info(doc) for doc in App.listDocuments().values()]}

    def documents_new(self, params):
        name = _name(params.get("name"))
        if name in App.listDocuments():
            raise BridgeError(INVALID_PARAMS, "Document already exists", {"document": name})
        label = params.get("label")
        if label is not None and not isinstance(label, str):
            raise invalid_params("Label must be a string", "label", label)
        doc = App.newDocument(name, label or name)
        return self._document_info(doc)

    def documents_activate(self, params):
        name = params.get("name")
        if not isinstance(name, str) or name not in App.listDocuments():
            raise BridgeError(INVALID_PARAMS, "Document not found", {"document": name})
        App.setActiveDocument(name)
        return self._document_info(App.getDocument(name))

    def documents_open(self, params):
        path = self.path_policy.resolve_read(params.get("path"), (".fcstd",))
        doc = App.openDocument(str(path))
        return self._document_info(doc)

    def documents_save(self, params):
        doc = self._document(params)
        path_value = params.get("path")
        if path_value is not None:
            path = self.path_policy.resolve_write(path_value, (".fcstd",))
            doc.saveAs(str(path))
        elif doc.FileName:
            doc.save()
        else:
            raise invalid_params("A path is required for an unsaved document", "path")
        return self._document_info(doc)

    def documents_close(self, params):
        doc = self._document(params)
        info = self._document_info(doc)
        App.closeDocument(doc.Name)
        return {"closed": info["name"]}

    def cad_create_box(self, params):
        """Deprecated alias; kept so older clients keep working."""
        return self.objects_create(
            {
                "document": params.get("document"),
                "name": params.get("name", "Box"),
                "label": params.get("label"),
                "kind": "box",
                "parameters": {key: params.get(key) for key in ("length", "width", "height")},
            }
        )

    def objects_create(self, params):
        kind = params.get("kind")
        if kind not in PRIMITIVES:
            raise invalid_params("Unsupported object kind", "kind", kind)
        type_id, fields = PRIMITIVES[kind]

        parameters = params.get("parameters")
        if not isinstance(parameters, dict):
            raise invalid_params("Parameters must be an object", "parameters", parameters)
        unknown = set(parameters) - {field for field, _, _ in fields}
        if unknown:
            raise invalid_params("Unknown parameters for this kind", "parameters", sorted(unknown))

        # Everything is validated before the document is touched, so a rejected
        # request never leaves a half-configured object behind.
        values = [
            (prop, _signed_number(parameters.get(field), field, sign))
            for field, prop, sign in fields
        ]
        if kind == "cone" and not any(value for prop, value in values if prop.startswith("Radius")):
            raise invalid_params("A cone needs at least one non-zero radius", "parameters", parameters)
        position = _vector_value(params.get("placement", [0.0, 0.0, 0.0]), "placement")
        rotation = _rotation(params.get("rotation"))

        doc = self._document(params)
        name, label = self._new_name(doc, params)
        obj = doc.addObject(type_id, name)
        obj.Label = label
        for prop, value in values:
            setattr(obj, prop, value)
        obj.Placement = App.Placement(App.Vector(*position), rotation)
        doc.recompute()
        return self._shape_info(doc, obj)

    def objects_list(self, params):
        doc = self._document(params)
        objects = []
        for obj in doc.Objects:
            shape = self._topo_shape(obj)
            objects.append(
                {
                    "name": obj.Name,
                    "label": obj.Label,
                    "type_id": obj.TypeId,
                    "visible": bool(getattr(obj, "Visibility", True)),
                    "has_shape": shape is not None and not shape.isNull(),
                    "used_by": [parent.Name for parent in obj.InList],
                }
            )
        return {"document": doc.Name, "objects": objects}

    def objects_delete(self, params):
        doc, obj = self._object(params)
        dependents = [parent.Name for parent in obj.InList]
        if dependents:
            raise BridgeError(
                INVALID_PARAMS,
                "Object is still used by other objects",
                {"object": obj.Name, "used_by": dependents},
            )
        name = obj.Name
        doc.removeObject(name)
        doc.recompute()
        return {"document": doc.Name, "deleted": name}

    def objects_get_properties(self, params):
        doc, obj = self._object(params)
        requested = params.get("properties")
        if requested is None:
            names = list(obj.PropertiesList)
        else:
            if not isinstance(requested, list) or not requested:
                raise invalid_params("Properties must be a non-empty list", "properties", requested)
            names = []
            for item in requested:
                if not isinstance(item, str) or item not in obj.PropertiesList:
                    raise BridgeError(
                        INVALID_PARAMS,
                        "Property not found",
                        {"object": obj.Name, "property": item},
                    )
                names.append(item)

        properties = {}
        unsupported = []
        for name in names:
            kind, type_id = self._property_kind(obj, name)
            if kind is None:
                unsupported.append({"name": name, "type_id": type_id})
                continue
            entry = {
                "type_id": type_id,
                "value": self._read_property(obj, name, kind),
                "read_only": "ReadOnly" in obj.getEditorMode(name),
            }
            if kind == "enum":
                entry["options"] = list(obj.getEnumerationsOfProperty(name))
            properties[name] = entry
        return {
            "document": doc.Name,
            "object": obj.Name,
            "properties": properties,
            "unsupported": unsupported,
        }

    def objects_set_properties(self, params):
        doc, obj = self._object(params)
        values = params.get("values")
        if not isinstance(values, dict) or not values:
            raise invalid_params("Values must be a non-empty object", "values", values)

        # Resolve and validate every assignment before applying any of them.
        assignments = []
        for name, raw in values.items():
            if name not in obj.PropertiesList:
                raise BridgeError(
                    INVALID_PARAMS,
                    "Property not found",
                    {"object": obj.Name, "property": name, "available": sorted(obj.PropertiesList)},
                )
            kind, type_id = self._property_kind(obj, name)
            if kind is None:
                raise BridgeError(
                    INVALID_PARAMS,
                    "Property type cannot be written through the Bridge",
                    {"property": name, "type_id": type_id},
                )
            if "ReadOnly" in obj.getEditorMode(name):
                raise BridgeError(INVALID_PARAMS, "Property is read-only", {"property": name})
            assignments.append((name, self._coerce_property(obj, name, kind, raw)))

        for name, value in assignments:
            setattr(obj, name, value)
        doc.recompute()
        return self.objects_get_properties(
            {"document": doc.Name, "object": obj.Name, "properties": sorted(values)}
        )

    def objects_transform(self, params):
        doc, obj = self._object(params)
        if "position" not in params and "rotation" not in params:
            raise invalid_params("Provide a position, a rotation, or both", "position")
        relative = params.get("relative", False)
        if not isinstance(relative, bool):
            raise invalid_params("Relative must be a boolean", "relative", relative)
        position = App.Vector(*_vector_value(params.get("position", [0.0, 0.0, 0.0]), "position"))
        rotation = _rotation(params.get("rotation"))

        if relative:
            obj.Placement = App.Placement(position, rotation).multiply(obj.Placement)
        else:
            current = obj.Placement
            obj.Placement = App.Placement(
                position if "position" in params else current.Base,
                rotation if "rotation" in params else current.Rotation,
            )
        doc.recompute()
        return self._shape_info(doc, obj)

    def objects_boolean(self, params):
        operation = params.get("operation")
        type_id = BOOLEAN_OPERATIONS.get(operation)
        if type_id is None:
            raise invalid_params("Unsupported boolean operation", "operation", operation)
        names = params.get("objects")
        if not isinstance(names, list) or len(names) < 2:
            raise invalid_params("A boolean needs at least two operand names", "objects", names)
        if operation == "cut" and len(names) != 2:
            raise invalid_params("A cut takes exactly two operands", "objects", names)
        if len(set(names)) != len(names):
            raise invalid_params("Operands must be distinct", "objects", names)

        doc = self._document(params)
        operands = []
        for item in names:
            operand = doc.getObject(item) if isinstance(item, str) else None
            if operand is None:
                raise BridgeError(
                    INVALID_PARAMS, "Object not found", {"document": doc.Name, "object": item}
                )
            shape = getattr(operand, "Shape", None)
            if shape is None or shape.isNull():
                raise BridgeError(INVALID_PARAMS, "Operand has no shape", {"object": operand.Name})
            operands.append(operand)
        name, label = self._new_name(doc, params)

        result = doc.addObject(type_id, name)
        result.Label = label
        if operation == "cut":
            result.Base, result.Tool = operands
        else:
            result.Shapes = operands
        doc.recompute()

        shape = getattr(result, "Shape", None)
        if "Invalid" in result.State or shape is None or shape.isNull():
            doc.removeObject(result.Name)
            doc.recompute()
            raise BridgeError(
                INVALID_PARAMS,
                "Boolean operation produced no valid shape",
                {"operation": operation, "objects": names},
            )
        return self._shape_info(doc, result)

    def cad_inspect_object(self, params):
        doc, obj = self._object(params)
        doc.recompute()
        return self._shape_info(doc, obj)

    def cad_list_faces(self, params):
        doc, obj = self._object(params)
        doc.recompute()
        shape = self._topo_shape(obj)
        if shape is None or shape.isNull():
            raise BridgeError(INVALID_PARAMS, "Object has no solid shape", {"object": obj.Name})
        return {
            "document": doc.Name,
            "object": obj.Name,
            "faces": [self._face_info(index, face) for index, face in enumerate(shape.Faces, 1)],
        }

    def cad_find_planar_faces(self, params):
        face_result = self.cad_list_faces(params)
        axis = params.get("axis")
        value = params.get("value")
        tolerance = params.get("tolerance", 1e-7)
        normal = params.get("normal")
        normal_tolerance = params.get("normal_tolerance", 1e-6)

        if axis not in ("x", "y", "z"):
            raise invalid_params("Axis must be x, y, or z", "axis", axis)
        value = _finite_number(value, "value")
        tolerance = _finite_number(tolerance, "tolerance")
        normal_tolerance = _finite_number(normal_tolerance, "normal_tolerance")
        if tolerance < 0:
            raise invalid_params("Tolerance must be non-negative", "tolerance", tolerance)
        if normal_tolerance < 0:
            raise invalid_params(
                "Normal tolerance must be non-negative", "normal_tolerance", normal_tolerance
            )
        if normal is not None:
            if not isinstance(normal, list) or len(normal) != 3:
                raise invalid_params("Normal must be a three-item list", "normal", normal)
            normal = [_finite_number(item, "normal") for item in normal]

        axis_index = {"x": 0, "y": 1, "z": 2}[axis]
        matches = []
        for face in face_result["faces"]:
            if not face["planar"]:
                continue
            if abs(face["center"][axis_index] - value) > tolerance:
                continue
            if normal is not None:
                if any(
                    abs(face["normal"][index] - normal[index]) > normal_tolerance
                    for index in range(3)
                ):
                    continue
            matches.append(face)
        return {
            "document": face_result["document"],
            "object": face_result["object"],
            "matches": matches,
        }

    def io_import_step(self, params):
        path = self.path_policy.resolve_read(params.get("path"), (".step", ".stp"))
        doc = self._document(params)
        before = {obj.Name for obj in doc.Objects}
        Import.insert(str(path), doc.Name)
        doc.recompute()
        created = [obj.Name for obj in doc.Objects if obj.Name not in before]
        return {"document": doc.Name, "path": str(path), "created_objects": created}

    def io_export_step(self, params):
        path = self.path_policy.resolve_write(params.get("path"), (".step", ".stp"))
        doc = self._document(params)
        names = params.get("objects")
        if names is None:
            objects = [obj for obj in doc.Objects if hasattr(obj, "Shape") and not obj.Shape.isNull()]
        else:
            if not isinstance(names, list) or not names:
                raise invalid_params("Objects must be a non-empty list", "objects", names)
            objects = []
            for name in names:
                obj = doc.getObject(name) if isinstance(name, str) else None
                if obj is None:
                    raise BridgeError(INVALID_PARAMS, "Object not found", {"object": name})
                objects.append(obj)
        if not objects:
            raise BridgeError(INVALID_PARAMS, "No exportable objects found")
        Import.export(objects, str(path))
        return {"document": doc.Name, "path": str(path), "objects": [obj.Name for obj in objects]}

    # --- FEM ---------------------------------------------------------------
    # One generic factory plus the existing property API, rather than a method
    # per constraint type. Everything a constraint needs beyond creation is an
    # ordinary property, including its geometry references.

    @staticmethod
    def _fem_module(name):
        try:
            return __import__(name, fromlist=["*"])
        except ImportError as exc:
            raise BridgeError(
                INTERNAL_ERROR,
                "FreeCAD FEM module is not available",
                {"module": name, "detail": str(exc)},
            )

    def _member(self, doc, params, field, type_id):
        name = params.get(field)
        obj = doc.getObject(name) if isinstance(name, str) else None
        if obj is None or not obj.isDerivedFrom(type_id):
            raise BridgeError(
                INVALID_PARAMS,
                "Expected an existing {} object".format(type_id),
                {field: name},
            )
        return obj

    def fem_create(self, params):
        kind = params.get("kind")
        factory = FEM_KINDS.get(kind)
        if factory is None:
            raise invalid_params("Unsupported FEM object kind", "kind", kind)
        doc = self._document(params)
        name, label = self._new_name(doc, params)
        analysis = None
        if params.get("analysis") is not None:
            analysis = self._member(doc, params, "analysis", "Fem::FemAnalysis")

        objects_fem = self._fem_module("ObjectsFem")
        obj = getattr(objects_fem, factory)(doc, name)
        obj.Label = label
        if analysis is not None:
            analysis.addObject(obj)
        doc.recompute()
        return {
            "document": doc.Name,
            "name": obj.Name,
            "label": obj.Label,
            "type_id": obj.TypeId,
            # Returned so a client can discover what to set next without
            # needing a per-type schema.
            "properties": sorted(obj.PropertiesList),
        }

    def fem_mesh(self, params):
        doc, obj = self._object(params)
        gmshtools = self._fem_module("femmesh.gmshtools")
        error = gmshtools.GmshTools(obj).create_mesh()
        doc.recompute()
        mesh = getattr(obj, "FemMesh", None)
        result = {
            "document": doc.Name,
            "object": obj.Name,
            "error": str(error) if error else None,
        }
        if mesh is not None:
            result.update(
                {
                    "nodes": mesh.NodeCount,
                    "edges": mesh.EdgeCount,
                    "faces": mesh.FaceCount,
                    "volumes": mesh.VolumeCount,
                    "tetra": mesh.TetraCount,
                    "hexa": mesh.HexaCount,
                }
            )
        return result

    def fem_solve(self, params):
        doc = self._document(params)
        analysis = self._member(doc, params, "analysis", "Fem::FemAnalysis")
        solver = self._member(doc, params, "solver", "App::DocumentObject")
        working_dir = self.path_policy.resolve_directory(params.get("working_dir"))

        ccxtools = self._fem_module("femtools.ccxtools")
        fea = ccxtools.FemToolsCcx(analysis, solver)
        fea.update_objects()
        # The working directory is itself one of the prerequisites, so it has to
        # be set before the check runs.
        fea.setup_working_dir(str(working_dir))
        blocked = fea.check_prerequisites()
        if blocked:
            raise BridgeError(
                INVALID_PARAMS, "Analysis is not ready to solve", {"detail": str(blocked)}
            )
        fea.purge_results()
        fea.write_inp_file()
        if not getattr(fea, "inp_file_name", None):
            raise BridgeError(INTERNAL_ERROR, "CalculiX input file was not written")
        fea.setup_ccx()
        # A failed solve must come back as a diagnosis, not as an exception.
        # FreeCAD's own post-run code also raises on side paths (for example an
        # empty .dat file leaves it dereferencing a None text object), and that
        # must not hide a result that did land.
        warnings = []
        for stage in ("ccx_run", "load_results"):
            try:
                getattr(fea, stage)()
            except Exception as exc:
                warnings.append("{}: {}: {}".format(stage, type(exc).__name__, exc))
        doc.recompute()

        stdout = str(getattr(fea, "ccx_stdout", "") or "")
        solver_errors = sorted(
            {line.strip() for line in stdout.splitlines() if "*ERROR" in line}
        )

        results = []
        for member in analysis.Group:
            if not member.isDerivedFrom("Fem::FemResultObject"):
                continue
            entry = {"name": member.Name}
            for field, key in (
                ("vonMises", "von_mises_max"),
                ("DisplacementLengths", "displacement_max"),
                ("MaxShear", "max_shear_max"),
            ):
                values = getattr(member, field, None)
                if values:
                    entry[key] = float(max(values))
                    if key == "von_mises_max":
                        entry["von_mises_min"] = float(min(values))
            results.append(entry)

        return {
            "document": doc.Name,
            "analysis": analysis.Name,
            "solved": bool(results) and not solver_errors,
            "inp_file": str(fea.inp_file_name),
            "working_dir": str(working_dir),
            "solver_errors": solver_errors[:20],
            "warnings": warnings,
            "ccx_stdout_tail": stdout[-1500:],
            "results": results,
        }

    def gui_activate_workbench(self, params):
        name = params.get("name")
        if not isinstance(name, str) or not name:
            raise invalid_params("Workbench name must be a non-empty string", "name", name)
        available = Gui.listWorkbenches()
        if name not in available:
            raise BridgeError(
                INVALID_PARAMS,
                "Workbench not found",
                {"workbench": name, "available": sorted(available)},
            )
        Gui.activateWorkbench(name)
        return {"workbench": Gui.activeWorkbench().name()}

    def gui_set_view(self, params):
        view_name = params.get("view")
        actions = {
            "axonometric": "viewAxonometric",
            "front": "viewFront",
            "rear": "viewRear",
            "left": "viewLeft",
            "right": "viewRight",
            "top": "viewTop",
            "bottom": "viewBottom",
        }
        action = actions.get(view_name)
        if action is None:
            raise invalid_params("Unsupported view", "view", view_name)
        view = self._active_view()
        with _without_navigation_animation():
            getattr(view, action)()
        Gui.updateGui()
        return {"view": view_name}

    def gui_fit_all(self, params):
        del params
        view = self._active_view()
        with _without_navigation_animation():
            view.fitAll()
        Gui.updateGui()
        return {"fitted": True}

    def gui_save_screenshot(self, params):
        path = self.path_policy.resolve_write(params.get("path"), (".png", ".jpg", ".jpeg"))
        width = params.get("width", 1600)
        height = params.get("height", 1000)
        for field, value in (("width", width), ("height", height)):
            if isinstance(value, bool) or not isinstance(value, int) or not 64 <= value <= 8192:
                raise invalid_params("Image dimension must be an integer from 64 to 8192", field, value)
        self._active_view().saveImage(str(path), width, height, "Current")
        return {"path": str(path), "width": width, "height": height}

    @staticmethod
    def _active_view():
        if App.ActiveDocument is None or Gui.activeDocument() is None:
            raise BridgeError(INVALID_PARAMS, "No active GUI document")
        return Gui.activeDocument().activeView()

    @staticmethod
    def _topo_shape(obj):
        """Return obj's TopoShape, or None.

        Not every Shape property is geometry: a FEM mesh object's Shape is a
        link to the part it meshes, so the attribute alone is not enough.
        """
        shape = getattr(obj, "Shape", None)
        return shape if hasattr(shape, "isNull") else None

    @staticmethod
    def _shape_info(doc, obj):
        shape = FreeCADAPI._topo_shape(obj)
        result = {
            "document": doc.Name,
            "name": obj.Name,
            "label": obj.Label,
            "type_id": obj.TypeId,
            "has_shape": shape is not None and not shape.isNull(),
        }
        if result["has_shape"]:
            bounds = shape.BoundBox
            result.update(
                {
                    "volume": float(shape.Volume),
                    "area": float(shape.Area),
                    "solid_count": len(shape.Solids),
                    "face_count": len(shape.Faces),
                    "bounding_box": {
                        "min": [float(bounds.XMin), float(bounds.YMin), float(bounds.ZMin)],
                        "max": [float(bounds.XMax), float(bounds.YMax), float(bounds.ZMax)],
                        "size": [float(bounds.XLength), float(bounds.YLength), float(bounds.ZLength)],
                    },
                    "placement": _vector(obj.Placement.Base),
                }
            )
        return result

    @staticmethod
    def _face_info(index, face):
        parameter_range = face.ParameterRange
        u = (parameter_range[0] + parameter_range[1]) / 2.0
        v = (parameter_range[2] + parameter_range[3]) / 2.0
        normal = face.normalAt(u, v)
        surface_type = type(face.Surface).__name__
        return {
            "index": index,
            "name": "Face{}".format(index),
            "surface_type": surface_type,
            "planar": surface_type == "Plane",
            "area": float(face.Area),
            "center": _vector(face.CenterOfMass),
            "normal": _vector(normal),
        }
