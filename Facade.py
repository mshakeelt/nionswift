"""
    A versioned interface to Swift.

    on_xyz methods are used when a callback needs a return value and has only a single listener.

    events are used when a callback is optional and may have multiple listeners.

    Versions numbering follows semantic versioning: http://semver.org/
"""

# standard libraries
import datetime

# third party libraries
# None

# local libraries
from nion.swift.model import DataItem
from nion.swift.model import Operation
from nion.swift.model import Image
from nion.swift import Application
from nion.swift import Panel
from nion.swift import Workspace
from nion.ui import CanvasItem
from nion.ui import Geometry


__all__ = ["load"]


class FacadeCanvasItem(CanvasItem.AbstractCanvasItem):

    def __init__(self):
        super(FacadeCanvasItem, self).__init__()
        self.on_repaint = None

    def _repaint(self, drawing_context):
        if self.on_repaint:
            self.on_repaint(drawing_context, Geometry.IntSize.make(self.canvas_size))


class FacadeRootCanvasItem(CanvasItem.RootCanvasItem):

    def __init__(self, ui, canvas_item, properties):
        super(FacadeRootCanvasItem, self).__init__(ui, properties)
        self.__canvas_item = canvas_item

    @property
    def _widget(self):
        return self.canvas_widget

    @property
    def on_repaint(self):
        return self.__canvas_item.on_repaint

    @on_repaint.setter
    def on_repaint(self, value):
        self.__canvas_item.on_repaint = value


class FacadeColumnWidget(object):

    def __init__(self, ui):
        self.__ui = ui
        self.__column_widget = self.__ui.create_column_widget()

    @property
    def _widget(self):
        return self.__column_widget

    def add_spacing(self, spacing):
        self.__column_widget.add_spacing(spacing)

    def add_stretch(self):
        self.__column_widget.add_stretch()

    def add(self, widget):
        self.__column_widget.add(widget._widget)


class FacadeRowWidget(object):

    def __init__(self, ui):
        self.__ui = ui
        self.__row_widget = self.__ui.create_row_widget()

    @property
    def _widget(self):
        return self.__row_widget

    def add_spacing(self, spacing):
        self.__row_widget.add_spacing(spacing)

    def add_stretch(self):
        self.__row_widget.add_stretch()

    def add(self, widget):
        self.__row_widget.add(widget._widget)


class FacadeLabelWidget(object):

    def __init__(self, ui):
        self.__ui = ui
        self.__label_widget = self.__ui.create_label_widget()

    @property
    def _widget(self):
        return self.__label_widget

    @property
    def text(self):
        return self.__label_widget.text

    @text.setter
    def text(self, value):
        self.__label_widget.text = value


class FacadeLineEditWidget(object):

    def __init__(self, ui):
        self.__ui = ui
        self.__line_edit_widget = self.__ui.create_line_edit_widget()

    @property
    def _widget(self):
        return self.__line_edit_widget

    @property
    def text(self):
        return self.__line_edit_widget.text

    @text.setter
    def text(self, value):
        self.__line_edit_widget.text = value

    @property
    def on_editing_finished(self):
        return self.__line_edit_widget.on_editing_finished

    @on_editing_finished.setter
    def on_editing_finished(self, value):
        self.__line_edit_widget.on_editing_finished = value

    def select_all(self):
        self.__line_edit_widget.select_all()


class FacadePushButtonWidget(object):

    def __init__(self, ui):
        self.__ui = ui
        self.__push_button_widget = self.__ui.create_push_button_widget()

    @property
    def _widget(self):
        return self.__push_button_widget

    @property
    def text(self):
        return self.__push_button_widget.text

    @text.setter
    def text(self, value):
        self.__push_button_widget.text = value

    @property
    def on_clicked(self):
        return self.__push_button_widget.on_clicked

    @on_clicked.setter
    def on_clicked(self, value):
        self.__push_button_widget.on_clicked = value


class FacadeUserInterface(object):

    def __init__(self, manifest, ui):
        version = manifest.get("ui", "0")
        version_components = version.split(".")
        if int(version_components[0]) != 1 or len(version_components) > 1:
            raise NotImplementedError("Facade version %s is not available." % version)

        self.__manifest = manifest
        self.__ui = ui

    def create_canvas_widget(self, height=None):
        properties = dict()
        if height is not None:
            properties["min-height"] = height
            properties["max-height"] = height
        canvas_item = FacadeCanvasItem()
        root_canvas_item = FacadeRootCanvasItem(self.__ui, canvas_item, properties=properties)
        root_canvas_item.add_canvas_item(canvas_item)
        return root_canvas_item

    def create_column_widget(self):
        return FacadeColumnWidget(self.__ui)

    def create_row_widget(self):
        return FacadeRowWidget(self.__ui)

    def create_label_widget(self, text=None):
        label_widget = FacadeLabelWidget(self.__ui)
        label_widget.text = text
        return label_widget

    def create_line_edit_widget(self, text=None):
        line_edit_widget = FacadeLineEditWidget(self.__ui)
        line_edit_widget.text = text
        return line_edit_widget

    def create_push_button_widget(self, text=None):
        push_button_widget = FacadePushButtonWidget(self.__ui)
        push_button_widget.text = text
        return push_button_widget


class FacadePanel(Panel.Panel):

    def __init__(self, document_controller, panel_id, properties):
        super(FacadePanel, self).__init__(document_controller, panel_id, panel_id)
        self.on_close = None

    def close(self):
        if self.on_close:
            self.on_close()


class FacadeDocumentController(object):

    def __init__(self, manifest, ui):
        self.__manifest = manifest
        self.__ui = ui


class Facade(object):

    def __init__(self, manifest):
        super(Facade, self).__init__()
        self.__manifest = manifest

    def create_data_and_metadata_from_data(self, data, intensity_calibration, dimensional_calibrations, metadata, timestamp=None):
        data_shape_and_dtype = Image.spatial_shape_from_data(data), data.dtype
        timestamp = timestamp if timestamp else datetime.datetime.utcnow()
        return Operation.DataAndCalibration(lambda: data, data_shape_and_dtype, intensity_calibration, dimensional_calibrations, metadata, timestamp)

    def create_float_rect(self, o, s):
        return Geometry.FloatRect(o, s)

    def create_float_rect_from_tuple(self, origin_size):
        return Geometry.FloatRect(origin_size[0], origin_size[1])

    def create_float_rect_from_center_and_size(self, c, s):
        return Geometry.FloatRect.from_center_and_size(c, s)

    def create_float_point(self, y, x):
        return Geometry.FloatPoint(y, x)

    def create_float_point_from_tuple(self, y_x):
        return Geometry.FloatPoint(y_x[0], y_x[1])

    def create_float_size(self, h, w):
        return Geometry.FloatSize(h, w)

    def create_float_size_from_tuple(self, height_width):
        return Geometry.FloatSize(height_width[0], height_width[1])

    def create_int_rect(self, o, s):
        return Geometry.IntRect(o, s)

    def create_int_rect_from_tuple(self, origin_size):
        return Geometry.IntRect(origin_size[0], origin_size[1])

    def create_int_rect_from_center_and_size(self, c, s):
        return Geometry.IntRect.from_center_and_size(c, s)

    def create_int_point(self, y, x):
        return Geometry.IntPoint(y, x)

    def create_int_point_from_tuple(self, y_x):
        return Geometry.IntPoint(y_x[0], y_x[1])

    def create_int_size(self, h, w):
        return Geometry.IntSize(h, w)

    def create_int_size_from_tuple(self, height_width):
        return Geometry.IntSize(height_width[0], height_width[1])

    def create_panel(self, panel_delegate):
        """Create a utility panel that can be attached to a window.

         The panel_delegate should respond to the following:
            (property, read-only) panel_id
            (property, read-only) panel_name
            (property, read-only) panel_positions (a list from "top", "bottom", "left", "right", "all")
            (property, read-only) panel_position (from "top", "bottom", "left", "right", "none")
            (method, required) create_panel_widget(ui), returns a widget
            (method, optional) close()
        """

        panel_id = panel_delegate.panel_id
        panel_name = panel_delegate.panel_name
        panel_positions = getattr(panel_delegate, "panel_positions", ["left", "right"])
        panel_position = getattr(panel_delegate, "panel_position", "none")
        properties = getattr(panel_delegate, "panel_properties", None)

        def create_facade_panel(document_controller, panel_id, properties):
            panel = FacadePanel(document_controller, panel_id, properties)
            ui = FacadeUserInterface(self.__manifest, document_controller.ui)
            document_controller = FacadeDocumentController(self.__manifest, document_controller.ui)
            panel.widget = panel_delegate.create_panel_widget(ui, document_controller)._widget
            return panel

        workspace_manager = Workspace.WorkspaceManager()
        workspace_manager.register_panel(create_facade_panel, panel_id, panel_name, panel_positions, panel_position, properties)

    def create_unary_operation(self, unary_operation_delegate):

        class DelegateOperation(Operation.Operation):
            def __init__(self):
                super(DelegateOperation, self).__init__(unary_operation_delegate.operation_name, unary_operation_delegate.operation_id, unary_operation_delegate.operation_description)
                self.region_types = dict()
                self.region_bindings = dict()
                operation_region_bindings = getattr(unary_operation_delegate, "operation_region_bindings", dict())
                for operation_region_id, binding_description in operation_region_bindings.iteritems():
                    self.region_types[operation_region_id] = binding_description["type"]
                    for binding in binding_description["bindings"]:
                        for from_key, to_key in binding.iteritems():
                            self.region_bindings[operation_region_id] = [Operation.RegionBinding(from_key, to_key)]

            def get_processed_data_and_calibration(self, data_and_calibrations, values):
                # doesn't do any bounds checking
                return unary_operation_delegate.get_processed_data_and_metadata(data_and_calibrations[0], values)

        def apply_operation(document_controller):
            display_specifier = document_controller.selected_display_specifier
            buffered_data_source = display_specifier.buffered_data_source if display_specifier else None
            data_and_metadata = buffered_data_source.data_and_calibration if buffered_data_source else None
            if data_and_metadata and unary_operation_delegate.can_apply_to_data(data_and_metadata):
                operation = Operation.OperationItem(unary_operation_delegate.operation_id)
                for operation_region_id in getattr(unary_operation_delegate, "operation_region_bindings", dict()).keys():
                    operation.establish_associated_region(operation_region_id, buffered_data_source)
                return document_controller.add_processing_operation(display_specifier.buffered_data_source_specifier, operation, prefix=unary_operation_delegate.operation_prefix)
            return DataItem.DisplaySpecifier()

        def build_menus(document_controller):
            """ Make menu item for this operation. """
            document_controller.processing_menu.add_menu_item(unary_operation_delegate.operation_name, lambda: apply_operation(document_controller))

        Operation.OperationManager().register_operation(unary_operation_delegate.operation_id, lambda: DelegateOperation())
        Application.app.register_menu_handler(build_menus) # called on import to make the menu entry for this plugin


def load(manifest):
    """Load a facade interface matching the given version.

    version is a string and the only supported version is "1".
    """
    version = manifest.get("main", "0")
    version_components = version.split(".")
    if int(version_components[0]) != 1 or len(version_components) > 1:
        raise NotImplementedError("Facade version %s is not available." % version)
    return Facade(manifest)


# TODO: facade panels never get closed
