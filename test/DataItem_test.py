# standard libraries
import copy
import datetime
import gc
import logging
import math
import threading
import unittest
import weakref

# third party libraries
import numpy

# local libraries
from nion.swift import Application
from nion.swift.model import Calibration
from nion.swift.model import DataItem
from nion.swift.model import Display
from nion.swift.model import DocumentModel
from nion.swift.model import Graphics
from nion.swift.model import Image
from nion.swift.model import Operation
from nion.swift.model import Region
from nion.ui import Binding
from nion.ui import Observable
from nion.ui import Test


class TestCalibrationClass(unittest.TestCase):

    def test_conversion(self):
        calibration = Calibration.Calibration(3.0, 2.0, "x")
        self.assertEqual(calibration.convert_to_calibrated_value_str(5.0), u"13 x")

    def test_dependent_calibration(self):
        data_item = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        display_specifier.buffered_data_source.set_dimensional_calibration(0, Calibration.Calibration(3.0, 2.0, u"x"))
        display_specifier.buffered_data_source.set_dimensional_calibration(1, Calibration.Calibration(3.0, 2.0, u"x"))
        self.assertEqual(len(display_specifier.buffered_data_source.dimensional_calibrations), 2)
        data_item_copy = DataItem.DataItem()
        invert_operation = Operation.OperationItem("invert-operation")
        invert_operation.add_data_source(data_item._create_test_data_source())
        data_item_copy.set_operation(invert_operation)
        display_specifier2 = DataItem.DisplaySpecifier.from_data_item(data_item_copy)
        data_item_copy.recompute_data()
        dimensional_calibrations = display_specifier2.buffered_data_source.dimensional_calibrations
        self.assertEqual(len(dimensional_calibrations), 2)
        self.assertEqual(int(dimensional_calibrations[0].offset), 3)
        self.assertEqual(int(dimensional_calibrations[0].scale), 2)
        self.assertEqual(dimensional_calibrations[0].units, "x")
        self.assertEqual(int(dimensional_calibrations[1].offset), 3)
        self.assertEqual(int(dimensional_calibrations[1].scale), 2)
        self.assertEqual(dimensional_calibrations[1].units, "x")
        fft_operation = Operation.OperationItem("fft-operation")
        fft_operation.add_data_source(data_item._create_test_data_source())
        data_item_copy.set_operation(fft_operation)
        data_item_copy.recompute_data()
        dimensional_calibrations = display_specifier2.buffered_data_source.dimensional_calibrations
        self.assertEqual(int(dimensional_calibrations[0].offset), 0)
        self.assertEqual(dimensional_calibrations[0].units, "1/x")
        self.assertEqual(int(dimensional_calibrations[1].offset), 0)
        self.assertEqual(dimensional_calibrations[1].units, "1/x")

    def test_double_dependent_calibration(self):
        data_item = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        data_item2 = DataItem.DataItem()
        operation2 = Operation.OperationItem("resample-operation")
        operation2.add_data_source(data_item._create_test_data_source())
        data_item2.set_operation(operation2)
        data_item3 = DataItem.DataItem()
        operation3 = Operation.OperationItem("resample-operation")
        operation3.add_data_source(data_item2._create_test_data_source())
        data_item3.set_operation(operation3)
        display_specifier3 = DataItem.DisplaySpecifier.from_data_item(data_item3)
        display_specifier3.buffered_data_source.dimensional_calibrations

    def test_spatial_calibration_on_rgb(self):
        data_item = DataItem.DataItem(numpy.zeros((256, 256, 4), numpy.uint8))
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        self.assertTrue(Image.is_shape_and_dtype_2d(*display_specifier.buffered_data_source.data_shape_and_dtype))
        self.assertTrue(Image.is_shape_and_dtype_rgba(*display_specifier.buffered_data_source.data_shape_and_dtype))
        self.assertEqual(len(display_specifier.buffered_data_source.dimensional_calibrations), 2)

    def test_calibration_should_work_for_complex_data(self):
        calibration = Calibration.Calibration(1.0, 2.0, "c")
        value_array = numpy.zeros((1, ), dtype=numpy.complex128)
        value_array[0] = 3 + 4j
        self.assertEqual(calibration.convert_to_calibrated_value_str(value_array[0]), u"7+8j c")
        self.assertEqual(calibration.convert_to_calibrated_size_str(value_array[0]), u"6+8j c")

    def test_calibration_should_work_for_rgb_data(self):
        calibration = Calibration.Calibration(1.0, 2.0, "c")
        value = numpy.zeros((4, ), dtype=numpy.uint8)
        self.assertEqual(calibration.convert_to_calibrated_value_str(value), "0, 0, 0, 0")
        self.assertEqual(calibration.convert_to_calibrated_size_str(value), "0, 0, 0, 0")

    def test_calibration_conversion_to_string_can_handle_numpy_types(self):
        calibration = Calibration.Calibration(1.0, 2.0, "c")
        self.assertEqual(calibration.convert_to_calibrated_value_str(numpy.uint32(14)), "29 c")


class TestDataItemClass(unittest.TestCase):

    def setUp(self):
        self.app = Application.Application(Test.UserInterface(), set_global=False)

    def tearDown(self):
        pass

    def test_delete_data_item(self):
        data_item = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        weak_data_item = weakref.ref(data_item)
        data_item = None
        gc.collect()
        self.assertIsNone(weak_data_item())

    def test_copy_data_item(self):
        source_data_item = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        data = numpy.zeros((256, 256), numpy.uint32)
        data[128, 128] = 1000  # data range (0, 1000)
        data_item = DataItem.DataItem(data)
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        data_item.title = "data_item"
        metadata = data_item.metadata
        metadata.setdefault("test", dict())["one"] = 1
        metadata.setdefault("test", dict())["two"] = 22
        data_item.set_metadata(metadata)
        display_specifier.display.display_limits = (100, 900)
        invert_operation = Operation.OperationItem("invert-operation")
        invert_operation.add_data_source(source_data_item._create_test_data_source())
        data_item.set_operation(invert_operation)
        display_specifier.display.append_graphic(Graphics.RectangleGraphic())
        data_item_copy = copy.deepcopy(data_item)
        display_specifier2 = DataItem.DisplaySpecifier.from_data_item(data_item_copy)
        self.assertNotEqual(id(data), id(display_specifier2.buffered_data_source.data))
        # make sure properties and other items got copied
        #self.assertEqual(len(data_item_copy.properties), 19)  # not valid since properties only exist if in document
        self.assertIsNot(data_item.properties, data_item_copy.properties)
        # uuid should not match
        self.assertNotEqual(data_item.uuid, data_item_copy.uuid)
        self.assertEqual(data_item.writer_version, data_item_copy.writer_version)
        # metadata get copied?
        self.assertEqual(len(data_item.metadata.get("test")), 2)
        self.assertIsNot(data_item.metadata.get("test"), data_item_copy.metadata.get("test"))
        # make sure display counts match
        self.assertEqual(len(display_specifier.buffered_data_source.displays), len(display_specifier2.buffered_data_source.displays))
        self.assertEqual(data_item.operation.operation_id, data_item_copy.operation.operation_id)
        # tuples and strings are immutable, so test to make sure old/new are independent
        self.assertEqual(data_item.title, data_item_copy.title)
        data_item.title = "data_item1"
        self.assertNotEqual(data_item.title, data_item_copy.title)
        self.assertEqual(display_specifier.display.display_limits, display_specifier2.display.display_limits)
        display_specifier.display.display_limits = (150, 200)
        self.assertNotEqual(display_specifier.display.display_limits, display_specifier2.display.display_limits)
        # make sure dates are independent
        self.assertIsNot(data_item.created, data_item_copy.created)
        self.assertIsNot(display_specifier.buffered_data_source.created, display_specifier2.buffered_data_source.created)
        # make sure calibrations, operations, nor graphics are not shared
        self.assertNotEqual(display_specifier.buffered_data_source.dimensional_calibrations[0], display_specifier2.buffered_data_source.dimensional_calibrations[0])
        self.assertNotEqual(data_item.operation, data_item_copy.operation)
        self.assertNotEqual(display_specifier.display.graphics[0], display_specifier2.display.graphics[0])

    def test_copy_data_item_properly_copies_data_source_and_connects_it(self):
        document_model = DocumentModel.DocumentModel()
        # setup by adding data item and a dependent data item
        data_item2 = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        data_item2a = DataItem.DataItem()
        operation2a = Operation.OperationItem("resample-operation")
        operation2a.add_data_source(data_item2._create_test_data_source())
        data_item2a.set_operation(operation2a)
        document_model.append_data_item(data_item2)  # add this first
        document_model.append_data_item(data_item2a)  # add this second
        # verify
        self.assertEqual(data_item2a.operation.data_sources[0].source_data_item, data_item2)
        # copy the dependent item
        data_item2a_copy = copy.deepcopy(data_item2a)
        document_model.append_data_item(data_item2a_copy)
        # verify data source
        self.assertEqual(data_item2a.operation.data_sources[0].source_data_item, data_item2)
        self.assertEqual(data_item2a_copy.operation.data_sources[0].source_data_item, data_item2)

    def test_copy_data_item_with_crop(self):
        source_data_item = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        data_item = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        crop_operation = Operation.OperationItem("crop-operation")
        crop_operation.set_property("bounds", ((0.25,0.25), (0.5,0.5)))
        crop_operation.add_data_source(source_data_item._create_test_data_source())
        data_item.set_operation(crop_operation)
        data_item_copy = copy.deepcopy(data_item)
        self.assertNotEqual(data_item_copy.operation, data_item.operation)
        self.assertEqual(data_item_copy.operation.get_property("bounds"), data_item.operation.get_property("bounds"))

    def test_copy_data_item_with_transaction(self):
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.zeros((4, 4), numpy.uint32))
        document_model.append_data_item(data_item)
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        with document_model.data_item_transaction(data_item):
            with display_specifier.buffered_data_source.data_ref() as data_ref:
                data_ref.master_data = numpy.ones((4, 4), numpy.uint32)
                data_item_copy = copy.deepcopy(data_item)
        display_specifier2 = DataItem.DisplaySpecifier.from_data_item(data_item_copy)
        with display_specifier.buffered_data_source.data_ref() as data_ref:
            with display_specifier2.buffered_data_source.data_ref() as data_copy_accessor:
                self.assertEqual(data_copy_accessor.master_data.shape, (4, 4))
                self.assertTrue(numpy.array_equal(data_ref.master_data, data_copy_accessor.master_data))
                data_ref.master_data = numpy.ones((4, 4), numpy.uint32) + 1
                self.assertFalse(numpy.array_equal(data_ref.master_data, data_copy_accessor.master_data))

    def test_clear_thumbnail_when_data_item_changed(self):
        data_item = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        display = display_specifier.display
        self.assertTrue(display.is_cached_value_dirty("thumbnail_data"))
        display.get_processor("thumbnail").recompute_data(self.app.ui)
        self.assertIsNotNone(display.get_processed_data("thumbnail"))
        self.assertFalse(display.is_cached_value_dirty("thumbnail_data"))
        with display_specifier.buffered_data_source.data_ref() as data_ref:
            data_ref.master_data = numpy.zeros((256, 256), numpy.uint32)
        self.assertTrue(display.is_cached_value_dirty("thumbnail_data"))

    def test_thumbnail_1d(self):
        data_item = DataItem.DataItem(numpy.zeros((256), numpy.uint32))
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        self.assertIsNotNone(display_specifier.display.get_processed_data("thumbnail"))

    def test_thumbnail_marked_dirty_when_source_data_changed(self):
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.ones((256, 256), numpy.double))
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        document_model.append_data_item(data_item)
        data_item_inverted = DataItem.DataItem()
        invert_operation = Operation.OperationItem("invert-operation")
        invert_operation.add_data_source(data_item._create_test_data_source())
        data_item_inverted.set_operation(invert_operation)
        document_model.append_data_item(data_item_inverted)
        inverted_display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item_inverted)
        data_item_inverted.recompute_data()
        data_item_inverted_display = inverted_display_specifier.display
        data_item_inverted_display.get_processor("thumbnail").recompute_data(self.app.ui)
        data_item_inverted_display.get_processed_data("thumbnail")
        # here the data should be computed and the thumbnail should not be dirty
        self.assertFalse(data_item_inverted_display.is_cached_value_dirty("thumbnail_data"))
        # now the source data changes and the inverted data needs computing.
        # the thumbnail should also be dirty.
        with display_specifier.buffered_data_source.data_ref() as data_ref:
            data_ref.master_data = data_ref.master_data + 1.0
        data_item_inverted.recompute_data()
        self.assertTrue(data_item_inverted_display.is_cached_value_dirty("thumbnail_data"))

    def test_delete_nested_data_item(self):
        document_model = DocumentModel.DocumentModel()
        # setup by adding data item and a dependent data item
        data_item2 = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        data_item2a = DataItem.DataItem()
        operation2a = Operation.OperationItem("resample-operation")
        operation2a.add_data_source(data_item2._create_test_data_source())
        data_item2a.set_operation(operation2a)
        data_item2a1 = DataItem.DataItem()
        operation2a1 = Operation.OperationItem("resample-operation")
        operation2a1.add_data_source(data_item2a._create_test_data_source())
        data_item2a1.set_operation(operation2a1)
        document_model.append_data_item(data_item2)  # add this first
        document_model.append_data_item(data_item2a)  # add this second
        document_model.append_data_item(data_item2a1)
        # verify
        self.assertEqual(len(document_model.data_items), 3)
        # remove item (and implicitly its dependency)
        document_model.remove_data_item(data_item2a)
        self.assertEqual(len(document_model.data_items), 1)

    def test_copy_data_item_with_display_and_graphics_should_copy_graphics(self):
        data_item = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        rect_graphic = Graphics.RectangleGraphic()
        display_specifier.display.append_graphic(rect_graphic)
        self.assertEqual(len(display_specifier.display.graphics), 1)
        data_item_copy = copy.deepcopy(data_item)
        display_specifier2 = DataItem.DisplaySpecifier.from_data_item(data_item_copy)
        self.assertEqual(len(display_specifier2.display.graphics), 1)

    def disabled_test_data_item_data_changed(self):
        # it is not currently possible to have fine grained control of what type of data has changed
        # disabling this test until that capability re-appears.
        # TODO: split this large monolithic test into smaller parts (some done already)
        document_model = DocumentModel.DocumentModel()
        # set up the data items
        data_item = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        data_item_graphic = Graphics.LineGraphic()
        display_specifier.display.append_graphic(data_item_graphic)
        document_model.append_data_item(data_item)
        data_item2 = DataItem.DataItem()
        fft_operation = Operation.OperationItem("fft-operation")
        fft_operation.add_data_source(data_item._create_test_data_source())
        data_item2.set_operation(fft_operation)
        document_model.append_data_item(data_item2)
        display_specifier2 = DataItem.DisplaySpecifier.from_data_item(data_item2)
        data_item3 = DataItem.DataItem()
        ifft_operation = Operation.OperationItem("inverse-fft-operation")
        ifft_operation.add_data_source(data_item2._create_test_data_source())
        data_item3.set_operation(ifft_operation)
        document_model.append_data_item(data_item3)
        display_specifier3 = DataItem.DisplaySpecifier.from_data_item(data_item3)
        # establish listeners
        class Listener(object):
            def __init__(self):
                self.reset()
            def reset(self):
                self._data_changed = False
                self._display_changed = False
            def data_item_content_changed(self, data_item, changes):
                self._data_changed = self._data_changed or DataItem.DATA in changes
            def display_changed(self, display):
                self._display_changed = True
        listener = Listener()
        data_item.add_listener(listener)
        display_specifier.display.add_listener(listener)
        listener2 = Listener()
        data_item2.add_listener(listener2)
        display_specifier2.display.add_listener(listener2)
        listener3 = Listener()
        data_item3.add_listener(listener3)
        display_specifier3.display.add_listener(listener3)
        listeners = (listener, listener2, listener3)
        # changing the master data of the source should trigger a data changed message
        # subsequently that should trigger a changed message for dependent items
        map(Listener.reset, listeners)
        with display_specifier.buffered_data_source.data_ref() as data_ref:
            data_ref.master_data = numpy.zeros((256, 256), numpy.uint32)
        document_model.recompute_all()
        self.assertTrue(listener._data_changed and listener._display_changed)
        self.assertTrue(listener2._data_changed and listener2._display_changed)
        self.assertTrue(listener3._data_changed and listener3._display_changed)
        # changing the param of the source should trigger a display changed message
        # but no data changed. nothing should change on the dependent items.
        map(Listener.reset, listeners)
        data_item.title = "new title"
        self.assertTrue(not listener._data_changed and listener._display_changed)
        self.assertTrue(not listener2._data_changed and not listener2._display_changed)
        self.assertTrue(not listener3._data_changed and not listener3._display_changed)
        # changing a graphic on source should NOT change dependent data
        # it should change the primary data item display, but not its data
        map(Listener.reset, listeners)
        data_item_graphic.start = (0.8, 0.2)
        self.assertTrue(not listener._data_changed)
        self.assertTrue(listener._display_changed)
        self.assertTrue(not listener._data_changed and listener._display_changed)
        self.assertTrue(not listener2._data_changed and not listener2._display_changed)
        self.assertTrue(not listener3._data_changed and not listener3._display_changed)
        # changing the display limit of source should NOT change dependent data
        map(Listener.reset, listeners)
        display_specifier.display.display_limits = (0.1, 0.9)
        self.assertTrue(not listener._data_changed and listener._display_changed)
        self.assertTrue(not listener2._data_changed and not listener2._display_changed)
        self.assertTrue(not listener3._data_changed and not listener3._display_changed)
        # modify a calibration should NOT change dependent data, but should change dependent display
        map(Listener.reset, listeners)
        spatial_calibration_0 = display_specifier.buffered_data_source.dimensional_calibrations[0]
        spatial_calibration_0.offset = 1.0
        display_specifier.buffered_data_source.set_dimensional_calibration(0, spatial_calibration_0)
        self.assertTrue(not listener._data_changed and listener._display_changed)
        self.assertTrue(not listener2._data_changed and not listener2._display_changed)
        self.assertTrue(not listener3._data_changed and not listener3._display_changed)
        # add/remove an operation. should change primary and dependent data and display
        map(Listener.reset, listeners)
        source_data_item = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        document_model.append_data_item(source_data_item)
        invert_operation = Operation.OperationItem("invert-operation")
        invert_operation.add_data_source(source_data_item._create_test_data_source())
        data_item.set_operation(invert_operation)
        document_model.recompute_all()
        self.assertTrue(listener._data_changed and listener._display_changed)
        self.assertTrue(listener2._data_changed and listener2._display_changed)
        self.assertTrue(listener3._data_changed and listener3._display_changed)
        map(Listener.reset, listeners)
        data_item.set_operation(None)
        document_model.recompute_all()
        self.assertTrue(listener._data_changed and listener._display_changed)
        self.assertTrue(listener2._data_changed and listener2._display_changed)
        self.assertTrue(listener3._data_changed and listener3._display_changed)
        # add/remove a data item should NOT change data or dependent data or display
        map(Listener.reset, listeners)
        data_item4 = DataItem.DataItem()
        invert_operation4 = Operation.OperationItem("invert-operation")
        invert_operation4.add_data_source(data_item._create_test_data_source())
        data_item4.set_operation(invert_operation4)
        document_model.append_data_item(data_item4)
        self.assertTrue(not listener._data_changed and not listener._display_changed)
        self.assertTrue(not listener2._data_changed and not listener2._display_changed)
        self.assertTrue(not listener3._data_changed and not listener3._display_changed)
        map(Listener.reset, listeners)
        document_model.remove_data_item(data_item4)
        self.assertTrue(not listener._data_changed and not listener._display_changed)
        self.assertTrue(not listener2._data_changed and not listener2._display_changed)
        self.assertTrue(not listener3._data_changed and not listener3._display_changed)

    def disabled_test_changing_calibration_property_should_trigger_display_changed_but_not_data_changed(self):
        # it is not currently possible to have fine grained control of what type of data has changed
        # disabling this test until that capability re-appears.
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        document_model.append_data_item(data_item)
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        class Listener(object):
            def __init__(self):
                self._display_changed = False
                self._data_changed = False
            def data_item_content_changed(self, data_item, changes):
                self._data_changed = DataItem.DATA in changes
            def display_changed(self, display):
                self._display_changed = True
        listener = Listener()
        data_item.add_listener(listener)
        display_specifier.display.add_listener(listener)
        spatial_calibration_0 = display_specifier.buffered_data_source.dimensional_calibrations[0]
        spatial_calibration_0.offset = 1.0
        display_specifier.buffered_data_source.set_dimensional_calibration(0, spatial_calibration_0)
        self.assertFalse(listener._data_changed)
        self.assertTrue(listener._display_changed)

    def test_appending_data_item_should_trigger_recompute(self):
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        document_model.append_data_item(data_item)
        inverted_data_item = DataItem.DataItem()
        invert_operation = Operation.OperationItem("invert-operation")
        invert_operation.add_data_source(data_item._create_test_data_source())
        inverted_data_item.set_operation(invert_operation)
        document_model.append_data_item(inverted_data_item)
        document_model.recompute_all()
        inverted_display_specifier = DataItem.DisplaySpecifier.from_data_item(inverted_data_item)
        self.assertFalse(inverted_display_specifier.buffered_data_source.is_data_stale)

    def test_data_range(self):
        data_item = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        # test scalar
        xx, yy = numpy.meshgrid(numpy.linspace(0,1,256), numpy.linspace(0,1,256))
        with display_specifier.buffered_data_source.data_ref() as data_ref:
            data_ref.master_data = 50 * (xx + yy) + 25
            data_range = display_specifier.buffered_data_source.data_range
            self.assertEqual(data_range, (25, 125))
            # now test complex
            data_ref.master_data = numpy.zeros((256, 256), numpy.complex64)
            xx, yy = numpy.meshgrid(numpy.linspace(0,1,256), numpy.linspace(0,1,256))
            data_ref.master_data = (2 + xx * 10) + 1j * (3 + yy * 10)
        data_range = display_specifier.buffered_data_source.data_range
        data_min = math.log(math.sqrt(2*2 + 3*3))
        data_max = math.log(math.sqrt(12*12 + 13*13))
        self.assertEqual(int(data_min*1e6), int(data_range[0]*1e6))
        self.assertEqual(int(data_max*1e6), int(data_range[1]*1e6))

    def test_removing_dependent_data_item_with_graphic(self):
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        document_model.append_data_item(data_item)
        crop_data_item = DataItem.DataItem()
        crop_operation = Operation.OperationItem("crop-operation")
        crop_operation.add_data_source(data_item._create_test_data_source())
        crop_data_item.set_operation(crop_operation)
        document_model.append_data_item(crop_data_item)
        # should remove properly when shutting down.

    def test_removing_derived_data_item_updates_dependency_info_on_source(self):
        document_model = DocumentModel.DocumentModel()
        data_item1 = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        data_item1.title = "1"
        document_model.append_data_item(data_item1)
        data_item1a = DataItem.DataItem()
        data_item1a.title = "1a"
        operation1a = Operation.OperationItem("invert-operation")
        operation1a.add_data_source(data_item1._create_test_data_source())
        data_item1a.set_operation(operation1a)
        document_model.append_data_item(data_item1a)
        self.assertEqual(len(document_model.get_dependent_data_items(data_item1)), 1)
        document_model.remove_data_item(data_item1a)
        self.assertEqual(len(document_model.get_dependent_data_items(data_item1)), 0)

    def test_recomputing_data_should_not_leave_it_loaded(self):
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        document_model.append_data_item(data_item)
        inverted_data_item = DataItem.DataItem()
        invert_operation = Operation.OperationItem("invert-operation")
        invert_operation.add_data_source(data_item._create_test_data_source())
        inverted_data_item.set_operation(invert_operation)
        document_model.append_data_item(inverted_data_item)
        inverted_display_specifier = DataItem.DisplaySpecifier.from_data_item(inverted_data_item)
        inverted_data_item.recompute_data()
        self.assertFalse(inverted_display_specifier.buffered_data_source.is_data_loaded)

    def test_loading_dependent_data_should_not_cause_source_data_to_load(self):
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        document_model.append_data_item(data_item)
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        data_item_inverted = DataItem.DataItem()
        invert_operation = Operation.OperationItem("invert-operation")
        invert_operation.add_data_source(data_item._create_test_data_source())
        data_item_inverted.set_operation(invert_operation)
        document_model.append_data_item(data_item_inverted)
        inverted_display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item_inverted)
        # begin checks
        data_item_inverted.recompute_data()
        self.assertFalse(display_specifier.buffered_data_source.is_data_loaded)
        with inverted_display_specifier.buffered_data_source.data_ref() as d:
            self.assertFalse(display_specifier.buffered_data_source.is_data_loaded)
        self.assertFalse(display_specifier.buffered_data_source.is_data_loaded)

    def test_modifying_source_data_should_trigger_data_changed_notification_from_dependent_data(self):
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        document_model.append_data_item(data_item)
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        data_item_inverted = DataItem.DataItem()
        invert_operation = Operation.OperationItem("invert-operation")
        invert_operation.add_data_source(data_item._create_test_data_source())
        data_item_inverted.set_operation(invert_operation)
        document_model.append_data_item(data_item_inverted)
        inverted_display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item_inverted)
        data_item_inverted.recompute_data()
        class Listener(object):
            def __init__(self):
                self.data_changed = False
            def data_item_content_changed(self, data_item, changes):
                self.data_changed = self.data_changed or DataItem.DATA in changes
        listener = Listener()
        data_item_inverted.add_listener(listener)
        with display_specifier.buffered_data_source.data_ref() as data_ref:
            data_ref.master_data = numpy.ones((256, 256), numpy.uint32)
        data_item_inverted.recompute_data()
        self.assertTrue(listener.data_changed)
        self.assertFalse(display_specifier.buffered_data_source.is_data_stale)
        self.assertFalse(inverted_display_specifier.buffered_data_source.is_data_stale)

    def test_modifying_source_data_should_trigger_data_item_stale_from_dependent_data_item(self):
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        document_model.append_data_item(data_item)
        inverted_data_item = DataItem.DataItem()
        invert_operation = Operation.OperationItem("invert-operation")
        invert_operation.add_data_source(data_item._create_test_data_source())
        inverted_data_item.set_operation(invert_operation)
        document_model.append_data_item(inverted_data_item)
        inverted_display_specifier = DataItem.DisplaySpecifier.from_data_item(inverted_data_item)
        inverted_data_item.recompute_data()
        with display_specifier.buffered_data_source.data_ref() as data_ref:
            data_ref.master_data = numpy.ones((256, 256), numpy.uint32)
        self.assertTrue(inverted_display_specifier.buffered_data_source.is_data_stale)

    def test_modifying_source_data_should_queue_recompute_in_document_model(self):
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        document_model.append_data_item(data_item)
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        inverted_data_item = DataItem.DataItem()
        invert_operation = Operation.OperationItem("invert-operation")
        invert_operation.add_data_source(data_item._create_test_data_source())
        inverted_data_item.set_operation(invert_operation)
        document_model.append_data_item(inverted_data_item)
        inverted_display_specifier = DataItem.DisplaySpecifier.from_data_item(inverted_data_item)
        inverted_data_item.recompute_data()
        with display_specifier.buffered_data_source.data_ref() as data_ref:
            data_ref.master_data = numpy.ones((256, 256), numpy.uint32)
        self.assertTrue(inverted_display_specifier.buffered_data_source.is_data_stale)
        document_model.recompute_all()
        self.assertFalse(inverted_display_specifier.buffered_data_source.is_data_stale)

    def test_is_data_stale_should_propagate_to_data_items_dependent_on_source(self):
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        document_model.append_data_item(data_item)
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        inverted_data_item = DataItem.DataItem()
        invert_operation = Operation.OperationItem("invert-operation")
        invert_operation.add_data_source(data_item._create_test_data_source())
        inverted_data_item.set_operation(invert_operation)
        document_model.append_data_item(inverted_data_item)
        inverted_display_specifier = DataItem.DisplaySpecifier.from_data_item(inverted_data_item)
        inverted2_data_item = DataItem.DataItem()
        invert_operation2 = Operation.OperationItem("invert-operation")
        invert_operation2.add_data_source(inverted_data_item._create_test_data_source())
        inverted2_data_item.set_operation(invert_operation2)
        document_model.append_data_item(inverted2_data_item)
        inverted2_display_specifier = DataItem.DisplaySpecifier.from_data_item(inverted2_data_item)
        inverted2_data_item.recompute_data()
        with display_specifier.buffered_data_source.data_ref() as data_ref:
            data_ref.master_data = numpy.ones((256, 256), numpy.uint32)
        self.assertTrue(inverted_display_specifier.buffered_data_source.is_data_stale)
        inverted_data_item.recompute_data()
        self.assertTrue(inverted2_display_specifier.buffered_data_source.is_data_stale)

    def test_data_item_that_is_recomputed_notifies_listeners_of_a_single_data_change(self):
        # this test ensures that doing a recompute_data is efficient and doesn't produce
        # extra data_item_content_changed messages.
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        document_model.append_data_item(data_item)
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        inverted_data_item = DataItem.DataItem()
        invert_operation = Operation.OperationItem("invert-operation")
        invert_operation.add_data_source(data_item._create_test_data_source())
        inverted_data_item.set_operation(invert_operation)
        document_model.append_data_item(inverted_data_item)
        inverted_display_specifier = DataItem.DisplaySpecifier.from_data_item(inverted_data_item)
        inverted_data_item.recompute_data()
        self.assertFalse(inverted_display_specifier.buffered_data_source.is_data_stale)
        class Listener(object):
            def __init__(self):
                self.data_changed = 0
            def data_item_content_changed(self, data_item, changes):
                if DataItem.DATA in changes:
                    self.data_changed += 1
        listener = Listener()
        inverted_data_item.add_listener(listener)
        with display_specifier.buffered_data_source.data_ref() as data_ref:
            data_ref.master_data = numpy.ones((256, 256), numpy.uint32)
        self.assertTrue(inverted_display_specifier.buffered_data_source.is_data_stale)
        self.assertEqual(listener.data_changed, 0)
        inverted_data_item.recompute_data()
        self.assertFalse(inverted_display_specifier.buffered_data_source.is_data_stale)
        self.assertEqual(listener.data_changed, 1)

    class DummyOperation(Operation.Operation):
        def __init__(self):
            description = [ { "name": "Param", "property": "param", "type": "scalar", "default": 0.0 } ]
            super(TestDataItemClass.DummyOperation, self).__init__("Dummy", "dummy-operation", description)
            self.count = 0
        def get_processed_data(self, data_sources, values):
            self.count += 1
            return numpy.zeros((16, 16))

    def test_operation_data_gets_cached(self):
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        document_model.append_data_item(data_item)
        data_item_dummy = DataItem.DataItem()
        dummy_operation = TestDataItemClass.DummyOperation()
        Operation.OperationManager().register_operation("dummy-operation", lambda: dummy_operation)
        dummy_operation_item = Operation.OperationItem("dummy-operation")
        dummy_operation_item.add_data_source(data_item._create_test_data_source())
        data_item_dummy.set_operation(dummy_operation_item)
        document_model.append_data_item(data_item_dummy)
        dummy_display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item_dummy)
        data_item_dummy.recompute_data()
        with dummy_display_specifier.buffered_data_source.data_ref() as d:
            start_count = dummy_operation.count
            d.data
            self.assertEqual(dummy_operation.count, start_count)
            d.data
            self.assertEqual(dummy_operation.count, start_count)

    class SumOperation(Operation.Operation):

        def __init__(self):
            super(TestDataItemClass.SumOperation, self).__init__("Add2", "add2-operation")

        def get_processed_data(self, data_sources, values):
            result = None
            for data_source in data_sources:
                if result is None:
                    result = data_source.data
                else:
                    result += data_source.data
            return result

    def test_operation_with_multiple_data_sources_is_allowed(self):
        document_model = DocumentModel.DocumentModel()
        data_item1 = DataItem.DataItem(numpy.ones((256, 256), numpy.uint32))
        data_item2 = DataItem.DataItem(numpy.ones((256, 256), numpy.uint32))
        data_item3 = DataItem.DataItem(numpy.ones((256, 256), numpy.uint32))
        document_model.append_data_item(data_item1)
        document_model.append_data_item(data_item2)
        document_model.append_data_item(data_item3)
        data_item_sum = DataItem.DataItem()
        sum_operation = TestDataItemClass.SumOperation()
        Operation.OperationManager().register_operation("sum-operation", lambda: sum_operation)
        sum_operation_item = Operation.OperationItem("sum-operation")
        sum_operation_item.add_data_source(data_item1._create_test_data_source())
        sum_operation_item.add_data_source(data_item2._create_test_data_source())
        sum_operation_item.add_data_source(data_item3._create_test_data_source())
        data_item_sum.set_operation(sum_operation_item)
        data_item_sum.recompute_data()
        document_model.append_data_item(data_item_sum)
        summed_display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item_sum)
        summed_data = summed_display_specifier.buffered_data_source.data
        self.assertEqual(summed_data[0, 0], 3)

    def test_operation_with_composite_data_source_applies_composition_and_generates_correct_result(self):
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.ones((256, 256), numpy.float32))
        document_model.append_data_item(data_item)
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        crop_operation = Operation.OperationItem("crop-operation")
        crop_operation.set_property("bounds", ((0.25, 0.25), (0.5, 0.5)))
        crop_operation.add_data_source(data_item._create_test_data_source())
        invert_operation = Operation.OperationItem("invert-operation")
        invert_operation.add_data_source(crop_operation)
        inverted_data_item = DataItem.DataItem()
        inverted_data_item.set_operation(invert_operation)
        inverted_display_specifier = DataItem.DisplaySpecifier.from_data_item(inverted_data_item)
        inverted_data_item.recompute_data()
        self.assertEqual(inverted_display_specifier.buffered_data_source.data_shape, (128, 128))
        self.assertEqual(inverted_display_specifier.buffered_data_source.data_dtype, display_specifier.buffered_data_source.data_dtype)
        self.assertAlmostEqual(inverted_display_specifier.buffered_data_source.data[50, 50], -1.0)

    def test_adding_removing_data_item_with_crop_operation_updates_drawn_graphics(self):
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        document_model.append_data_item(data_item)
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        self.assertEqual(len(display_specifier.display.drawn_graphics), 0)
        data_item_crop = DataItem.DataItem()
        crop_operation = Operation.OperationItem("crop-operation")
        crop_operation.set_property("bounds", ((0.25, 0.25), (0.5, 0.5)))
        crop_operation.establish_associated_region("crop", display_specifier.buffered_data_source)
        crop_operation.add_data_source(data_item._create_test_data_source())
        self.assertEqual(len(display_specifier.display.drawn_graphics), 1)
        data_item_crop.set_operation(crop_operation)
        document_model.append_data_item(data_item_crop)
        self.assertEqual(len(display_specifier.display.drawn_graphics), 1)
        document_model.remove_data_item(data_item_crop)
        self.assertEqual(len(display_specifier.display.drawn_graphics), 0)

    def test_adding_removing_crop_operation_to_existing_data_item_updates_drawn_graphics(self):
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        document_model.append_data_item(data_item)
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        self.assertEqual(len(display_specifier.display.drawn_graphics), 0)
        data_item_crop = DataItem.DataItem()
        document_model.append_data_item(data_item_crop)
        crop_operation = Operation.OperationItem("crop-operation")
        crop_operation.set_property("bounds", ((0.25, 0.25), (0.5, 0.5)))
        crop_operation.establish_associated_region("crop", display_specifier.buffered_data_source)
        crop_operation.add_data_source(data_item._create_test_data_source())
        self.assertEqual(len(display_specifier.display.drawn_graphics), 1)
        data_item_crop.set_operation(crop_operation)
        self.assertEqual(len(display_specifier.display.drawn_graphics), 1)
        data_item_crop.set_operation(None)
        self.assertEqual(len(display_specifier.display.drawn_graphics), 0)

    def test_updating_operation_graphic_property_notifies_data_item(self):
        class Listener(object):
            def __init__(self):
                self.reset()
            def reset(self):
                self._display_changed = False
            def display_changed(self, display):
                self._display_changed = True
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        document_model.append_data_item(data_item)
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        listener = Listener()
        display_specifier.display.add_listener(listener)
        data_item_crop = DataItem.DataItem()
        crop_operation = Operation.OperationItem("crop-operation")
        crop_operation.set_property("bounds", ((0.25, 0.25), (0.5, 0.5)))
        crop_operation.establish_associated_region("crop", display_specifier.buffered_data_source)
        crop_operation.add_data_source(data_item._create_test_data_source())
        data_item_crop.set_operation(crop_operation)
        document_model.append_data_item(data_item_crop)
        listener.reset()
        display_specifier.display.drawn_graphics[0].bounds = ((0.2,0.3), (0.8,0.7))
        self.assertTrue(listener._display_changed)

    # necessary to make inspector display updated values properly
    def test_updating_operation_graphic_property_with_same_value_notifies_data_item(self):
        class Listener(object):
            def __init__(self):
                self.reset()
            def reset(self):
                self._display_changed = False
            def display_changed(self, display):
                self._display_changed = True
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        document_model.append_data_item(data_item)
        listener = Listener()
        display_specifier.display.add_listener(listener)
        data_item_crop = DataItem.DataItem()
        crop_operation = Operation.OperationItem("crop-operation")
        crop_operation.set_property("bounds", ((0.25, 0.25), (0.5, 0.5)))
        crop_operation.establish_associated_region("crop", display_specifier.buffered_data_source)
        crop_operation.add_data_source(data_item._create_test_data_source())
        data_item_crop.set_operation(crop_operation)
        document_model.append_data_item(data_item_crop)
        display_specifier.display.drawn_graphics[0].bounds = ((0.2,0.3), (0.8,0.7))
        listener.reset()
        display_specifier.display.drawn_graphics[0].bounds = ((0.2,0.3), (0.8,0.7))
        self.assertTrue(listener._display_changed)

    def test_updating_region_bounds_updates_crop_graphic(self):
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        document_model.append_data_item(data_item)
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        data_item_crop = DataItem.DataItem()
        crop_operation = Operation.OperationItem("crop-operation")
        crop_operation.set_property("bounds", ((0.25, 0.25), (0.5, 0.5)))
        crop_region = Region.RectRegion()
        DataItem.DisplaySpecifier.from_data_item(data_item).buffered_data_source.add_region(crop_region)
        crop_operation.establish_associated_region("crop", display_specifier.buffered_data_source, crop_region)
        crop_operation.add_data_source(data_item._create_test_data_source())
        data_item_crop.set_operation(crop_operation)
        document_model.append_data_item(data_item_crop)
        # verify assumptions
        self.assertEqual(crop_operation.get_property("bounds"), ((0.25, 0.25), (0.5, 0.5)))
        # operation should now match the region
        self.assertEqual(crop_region.center, (0.5, 0.5))
        self.assertEqual(crop_region.size, (0.5, 0.5))
        # make change and verify it changed
        crop_region.center = 0.6, 0.6
        bounds = crop_operation.get_property("bounds")
        self.assertAlmostEqual(bounds[0][0], 0.35)
        self.assertAlmostEqual(bounds[0][1], 0.35)
        self.assertAlmostEqual(bounds[1][0], 0.5)
        self.assertAlmostEqual(bounds[1][1], 0.5)

    def test_snapshot_should_copy_raw_metadata(self):
        data_item = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        metadata = data_item.metadata
        metadata.setdefault("test", dict())["one"] = 1
        data_item.set_metadata(metadata)
        data_item_copy = data_item.snapshot()
        self.assertEqual(data_item_copy.metadata.get("test")["one"], 1)

    def test_data_item_allows_adding_of_two_data_sources(self):
        document_model = DocumentModel.DocumentModel()
        data_item1 = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        document_model.append_data_item(data_item1)
        data_item2 = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        document_model.append_data_item(data_item2)
        data_item = DataItem.DataItem()
        invert_operation = Operation.OperationItem("invert-operation")
        invert_operation.add_data_source(data_item1._create_test_data_source())
        invert_operation.add_data_source(data_item2._create_test_data_source())
        data_item.set_operation(invert_operation)
        document_model.append_data_item(data_item)

    def test_data_item_allows_remove_second_of_two_data_sources(self):
        # two data sources are not currently supported
        document_model = DocumentModel.DocumentModel()
        data_item1 = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        document_model.append_data_item(data_item1)
        data_item2 = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        document_model.append_data_item(data_item2)
        data_item = DataItem.DataItem()
        invert_operation = Operation.OperationItem("invert-operation")
        invert_operation.add_data_source(data_item1._create_test_data_source())
        invert_operation.add_data_source(data_item2._create_test_data_source())
        data_item.set_operation(invert_operation)
        document_model.append_data_item(data_item)
        invert_operation.remove_data_source(invert_operation.data_sources[1])

    def test_region_graphic_gets_added_to_existing_display(self):
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        document_model.append_data_item(data_item)
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        self.assertEqual(len(display_specifier.display.drawn_graphics), 0)
        display_specifier.buffered_data_source.add_region(Region.PointRegion())
        self.assertEqual(len(display_specifier.display.drawn_graphics), 1)

    def test_region_graphic_gets_added_to_new_display(self):
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        document_model.append_data_item(data_item)
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        display_specifier.buffered_data_source.add_region(Region.PointRegion())
        display_specifier.buffered_data_source.add_display(Display.Display())
        self.assertEqual(len(display_specifier.buffered_data_source.displays[1].drawn_graphics), 1)

    # necessary to make inspector display updated values properly
    def test_adding_region_generates_display_changed(self):
        class Listener(object):
            def __init__(self):
                self.reset()
            def reset(self):
                self._display_changed = False
            def display_changed(self, display):
                self._display_changed = True
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.zeros((256, 256), numpy.uint32))
        document_model.append_data_item(data_item)
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        listener = Listener()
        display_specifier.display.add_listener(listener)
        crop_region = Region.RectRegion()
        buffered_data_source = display_specifier.buffered_data_source
        buffered_data_source.add_region(crop_region)
        self.assertTrue(listener._display_changed)
        listener.reset()
        buffered_data_source.remove_region(crop_region)
        self.assertTrue(listener._display_changed)

    def test_data_source_connects_if_added_after_data_item_is_already_in_document(self):
        document_model = DocumentModel.DocumentModel()
        # configure the source item
        data_item = DataItem.DataItem(numpy.zeros((2000,1000), numpy.double))
        document_model.append_data_item(data_item)
        # configure the dependent item
        data_item2 = DataItem.DataItem()
        document_model.append_data_item(data_item2)
        # add data source AFTER data_item2 is in library
        invert_operation = Operation.OperationItem("invert-operation")
        invert_operation.add_data_source(data_item._create_test_data_source())
        data_item2.set_operation(invert_operation)
        display_specifier2 = DataItem.DisplaySpecifier.from_data_item(data_item2)
        data_item2.recompute_data()
        # see if the data source got connected
        self.assertIsNotNone(display_specifier2.buffered_data_source.data)
        self.assertEqual(data_item2.operation.data_sources[0].source_data_item, data_item)

    def test_connecting_data_source_updates_dependent_data_items_property_on_source(self):
        document_model = DocumentModel.DocumentModel()
        # configure the source item
        data_item = DataItem.DataItem(numpy.zeros((2000,1000), numpy.double))
        document_model.append_data_item(data_item)
        # configure the dependent item
        data_item2 = DataItem.DataItem()
        invert_operation = Operation.OperationItem("invert-operation")
        invert_operation.add_data_source(data_item._create_test_data_source())
        data_item2.set_operation(invert_operation)
        document_model.append_data_item(data_item2)
        # make sure the dependency list is updated
        self.assertEqual(document_model.get_dependent_data_items(data_item), [data_item2])

    def test_begin_transaction_also_begins_transaction_for_dependent_data_item(self):
        document_model = DocumentModel.DocumentModel()
        # configure the source item
        data_item = DataItem.DataItem(numpy.zeros((2000,1000), numpy.double))
        document_model.append_data_item(data_item)
        # configure the dependent item
        data_item2 = DataItem.DataItem()
        invert_operation = Operation.OperationItem("invert-operation")
        invert_operation.add_data_source(data_item._create_test_data_source())
        data_item2.set_operation(invert_operation)
        document_model.append_data_item(data_item2)
        # begin the transaction
        with document_model.data_item_transaction(data_item):
            self.assertTrue(data_item.transaction_count > 0)
            self.assertTrue(data_item2.transaction_count > 0)
        self.assertEqual(data_item.transaction_count, 0)
        self.assertEqual(data_item2.transaction_count, 0)

    def test_data_item_added_to_data_item_under_transaction_becomes_transacted_too(self):
        document_model = DocumentModel.DocumentModel()
        # configure the source item
        data_item = DataItem.DataItem(numpy.zeros((2000,1000), numpy.double))
        document_model.append_data_item(data_item)
        # begin the transaction
        with document_model.data_item_transaction(data_item):
            # configure the dependent item
            data_item2 = DataItem.DataItem()
            invert_operation = Operation.OperationItem("invert-operation")
            invert_operation.add_data_source(data_item._create_test_data_source())
            data_item2.set_operation(invert_operation)
            document_model.append_data_item(data_item2)
            # check to make sure it is under transaction
            self.assertTrue(data_item.transaction_count > 0)
            self.assertTrue(data_item2.transaction_count > 0)
        self.assertEqual(data_item.transaction_count, 0)
        self.assertEqual(data_item2.transaction_count, 0)

    def test_data_item_added_to_data_item_under_transaction_configures_dependency(self):
        document_model = DocumentModel.DocumentModel()
        # configure the source item
        data_item = DataItem.DataItem(numpy.zeros((2000,1000), numpy.double))
        document_model.append_data_item(data_item)
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        # begin the transaction
        with document_model.data_item_transaction(data_item):
            data_item_crop1 = DataItem.DataItem()
            crop_operation = Operation.OperationItem("crop-operation")
            crop_operation.set_property("bounds", ((0.25, 0.25), (0.5, 0.5)))
            crop_region = Region.RectRegion()
            crop_operation.establish_associated_region("crop", display_specifier.buffered_data_source)
            crop_operation.add_data_source(data_item._create_test_data_source())
            data_item_crop1.set_operation(crop_operation)
            document_model.append_data_item(data_item_crop1)
            # change the bounds of the graphic
            display_specifier.display.drawn_graphics[0].bounds = ((0.31, 0.32), (0.6, 0.4))
            # make sure it is connected to the crop operation
            bounds = crop_operation.get_property("bounds")
            self.assertAlmostEqual(bounds[0][0], 0.31)
            self.assertAlmostEqual(bounds[0][1], 0.32)
            self.assertAlmostEqual(bounds[1][0], 0.6)
            self.assertAlmostEqual(bounds[1][1], 0.4)

    def test_data_item_under_transaction_added_to_document_does_write_delay(self):
        document_model = DocumentModel.DocumentModel()
        # configure the source item
        data_item = DataItem.DataItem(numpy.zeros((2000,1000), numpy.double))
        # begin the transaction
        with document_model.data_item_transaction(data_item):
            document_model.append_data_item(data_item)
            persistent_storage = data_item.managed_object_context.get_persistent_storage_for_object(data_item)
            self.assertTrue(persistent_storage.write_delayed)

    def test_data_item_added_to_live_data_item_becomes_live_and_unlive_based_on_parent_item(self):
        document_model = DocumentModel.DocumentModel()
        # configure the source item
        data_item = DataItem.DataItem(numpy.zeros((2000,1000), numpy.double))
        document_model.append_data_item(data_item)
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        with document_model.data_item_live(data_item):
            data_item_crop1 = DataItem.DataItem()
            crop_operation = Operation.OperationItem("crop-operation")
            crop_operation.set_property("bounds", ((0.25, 0.25), (0.5, 0.5)))
            crop_region = Region.RectRegion()
            crop_operation.establish_associated_region("crop", display_specifier.buffered_data_source, crop_region)
            crop_operation.add_data_source(data_item._create_test_data_source())
            data_item_crop1.set_operation(crop_operation)
            document_model.append_data_item(data_item_crop1)
            self.assertTrue(data_item_crop1.is_live)
        self.assertFalse(data_item.is_live)
        self.assertFalse(data_item_crop1.is_live)

    def test_data_item_removed_from_live_data_item_becomes_unlive(self):
        document_model = DocumentModel.DocumentModel()
        # configure the source item
        data_item = DataItem.DataItem(numpy.zeros((2000,1000), numpy.double))
        document_model.append_data_item(data_item)
        data_item_crop1 = DataItem.DataItem()
        sum_operation = TestDataItemClass.SumOperation()
        Operation.OperationManager().register_operation("sum-operation", lambda: sum_operation)
        sum_operation_item = Operation.OperationItem("sum-operation")
        sum_operation_item.add_data_source(data_item._create_test_data_source())
        data_item_crop1.set_operation(sum_operation_item)
        document_model.append_data_item(data_item_crop1)
        with document_model.data_item_live(data_item):
            # check assumptions
            self.assertTrue(data_item.is_live)
            self.assertTrue(data_item_crop1.is_live)
            sum_operation_item.remove_data_source(sum_operation_item.data_sources[0])
            self.assertFalse(data_item_crop1.is_live)
        self.assertFalse(data_item.is_live)
        self.assertFalse(data_item_crop1.is_live)

    def slow_test_dependent_data_item_removed_while_live_data_item_becomes_unlive(self):
        # an intermittent race condition. run several times. see the changes that accompanied
        # the addition of this code.
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.zeros((2000,1000), numpy.double))
        document_model.append_data_item(data_item)
        def live_it(n):
            for _ in range(n):
                with data_item.live():
                    pass
        thread = threading.Thread(target=live_it, args=(1000, )).start()
        with data_item.live():
            for _ in range(100):
                data_item_inverted = DataItem.DataItem()
                invert_operation = Operation.OperationItem("invert-operation")
                invert_operation.add_data_source(data_item._create_test_data_source())
                data_item_inverted.set_operation(invert_operation)
                document_model.append_data_item(data_item_inverted)
                document_model.remove_data_item(data_item_inverted)

    def test_changing_metadata_or_data_does_not_mark_the_data_as_stale(self):
        # changing metadata or data will override what has been computed
        # from the data sources, if there are any.
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.zeros((2000,1000), numpy.double))
        document_model.append_data_item(data_item)
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        self.assertFalse(display_specifier.buffered_data_source.is_data_stale)
        with display_specifier.buffered_data_source.data_ref() as data_ref:
            data_ref.master_data = numpy.zeros((256, 256), numpy.uint32)
        display_specifier.buffered_data_source.set_intensity_calibration(Calibration.Calibration())
        self.assertFalse(display_specifier.buffered_data_source.is_data_stale)

    def test_changing_metadata_or_data_does_not_mark_the_data_as_stale_for_data_item_with_data_source(self):
        # changing metadata or data will override what has been computed
        # from the data sources, if there are any.
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.zeros((2000,1000), numpy.double))
        document_model.append_data_item(data_item)
        copied_data_item = DataItem.DataItem()
        invert_operation = Operation.OperationItem("invert-operation")
        invert_operation.add_data_source(data_item._create_test_data_source())
        copied_data_item.set_operation(invert_operation)
        document_model.append_data_item(copied_data_item)
        copied_display_specifier = DataItem.DisplaySpecifier.from_data_item(copied_data_item)
        copied_data_item.recompute_data()
        self.assertFalse(copied_display_specifier.buffered_data_source.is_data_stale)
        copied_display_specifier.buffered_data_source.set_intensity_calibration(Calibration.Calibration())
        self.assertFalse(copied_display_specifier.buffered_data_source.is_data_stale)

    def test_adding_operation_should_mark_the_data_as_stale(self):
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.zeros((2000,1000), numpy.double))
        document_model.append_data_item(data_item)
        copied_data_item = DataItem.DataItem()
        blur_operation = Operation.OperationItem("gaussian-blur-operation")
        blur_operation.add_data_source(data_item._create_test_data_source())
        document_model.append_data_item(copied_data_item)
        copied_data_item.recompute_data()
        copied_data_item.set_operation(blur_operation)
        copied_display_specifier = DataItem.DisplaySpecifier.from_data_item(copied_data_item)
        self.assertTrue(copied_display_specifier.buffered_data_source.is_data_stale)

    def test_removing_operation_should_not_mark_the_data_as_stale(self):
        # is this test valid any more?
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.zeros((2000,1000), numpy.double))
        document_model.append_data_item(data_item)
        copied_data_item = DataItem.DataItem()
        blur_operation = Operation.OperationItem("gaussian-blur-operation")
        blur_operation.add_data_source(data_item._create_test_data_source())
        document_model.append_data_item(copied_data_item)
        copied_data_item.recompute_data()
        copied_data_item.set_operation(blur_operation)
        copied_display_specifier = DataItem.DisplaySpecifier.from_data_item(copied_data_item)
        self.assertTrue(copied_display_specifier.buffered_data_source.is_data_stale)
        copied_data_item.recompute_data()
        self.assertFalse(copied_display_specifier.buffered_data_source.is_data_stale)
        copied_data_item.set_operation(None)
        self.assertFalse(copied_display_specifier.buffered_data_source.is_data_stale)

    def test_changing_operation_should_mark_the_data_as_stale(self):
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.zeros((2000,1000), numpy.double))
        document_model.append_data_item(data_item)
        copied_data_item = DataItem.DataItem()
        blur_operation = Operation.OperationItem("gaussian-blur-operation")
        blur_operation.add_data_source(data_item._create_test_data_source())
        copied_data_item.set_operation(blur_operation)
        document_model.append_data_item(copied_data_item)
        copied_display_specifier = DataItem.DisplaySpecifier.from_data_item(copied_data_item)
        copied_data_item.recompute_data()
        self.assertFalse(copied_display_specifier.buffered_data_source.is_data_stale)
        blur_operation.set_property("sigma", 0.1)
        self.assertTrue(copied_display_specifier.buffered_data_source.is_data_stale)

    def test_reloading_stale_data_should_still_be_stale(self):
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.ones((2, 2), numpy.double))
        document_model.append_data_item(data_item)
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        inverted_data_item = DataItem.DataItem()
        invert_operation = Operation.OperationItem("invert-operation")
        invert_operation.add_data_source(data_item._create_test_data_source())
        inverted_data_item.set_operation(invert_operation)
        document_model.append_data_item(inverted_data_item)
        inverted_display_specifier = DataItem.DisplaySpecifier.from_data_item(inverted_data_item)
        inverted_data_item.recompute_data()
        self.assertFalse(inverted_display_specifier.buffered_data_source.is_data_stale)
        self.assertAlmostEqual(inverted_display_specifier.buffered_data_source.data[0, 0], -1.0)
        # now the source data changes and the inverted data needs computing.
        with display_specifier.buffered_data_source.data_ref() as data_ref:
            data_ref.master_data = data_ref.master_data + 2.0
        self.assertTrue(inverted_display_specifier.buffered_data_source.is_data_stale)
        # data is now unloaded and stale.
        self.assertFalse(inverted_display_specifier.buffered_data_source.is_data_loaded)
        self.assertTrue(inverted_display_specifier.buffered_data_source.is_data_stale)
        # don't recompute
        self.assertAlmostEqual(inverted_display_specifier.buffered_data_source.data[0, 0], -1.0)
        # data should still be stale
        self.assertTrue(inverted_display_specifier.buffered_data_source.is_data_stale)

    def test_recomputing_data_gives_correct_result(self):
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.ones((2, 2), numpy.double))
        document_model.append_data_item(data_item)
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        data_item_inverted = DataItem.DataItem()
        invert_operation = Operation.OperationItem("invert-operation")
        invert_operation.add_data_source(data_item._create_test_data_source())
        data_item_inverted.set_operation(invert_operation)
        document_model.append_data_item(data_item_inverted)
        inverted_display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item_inverted)
        data_item_inverted.recompute_data()
        self.assertAlmostEqual(inverted_display_specifier.buffered_data_source.data[0, 0], -1.0)
        # now the source data changes and the inverted data needs computing.
        with display_specifier.buffered_data_source.data_ref() as data_ref:
            data_ref.master_data = data_ref.master_data + 2.0
        data_item_inverted.recompute_data()
        self.assertAlmostEqual(inverted_display_specifier.buffered_data_source.data[0, 0], -3.0)

    def test_recomputing_data_does_not_notify_listeners_of_stale_data_unless_it_is_really_stale(self):
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.ones((2, 2), numpy.double))
        document_model.append_data_item(data_item)
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        self.assertTrue(display_specifier.buffered_data_source.is_cached_value_dirty("statistics_data"))
        document_model.recompute_all()
        display_specifier.buffered_data_source.get_processor("statistics").recompute_data(None)
        self.assertFalse(display_specifier.buffered_data_source.is_cached_value_dirty("statistics_data"))
        data_item.recompute_data()
        self.assertFalse(display_specifier.buffered_data_source.is_cached_value_dirty("statistics_data"))

    def test_recomputing_data_after_cached_data_is_called_gives_correct_result(self):
        # verify that this works, the more fundamental test is in test_reloading_stale_data_should_still_be_stale
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.ones((2, 2), numpy.double))
        document_model.append_data_item(data_item)
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        inverted_data_item = DataItem.DataItem()
        invert_operation = Operation.OperationItem("invert-operation")
        invert_operation.add_data_source(data_item._create_test_data_source())
        inverted_data_item.set_operation(invert_operation)
        document_model.append_data_item(inverted_data_item)
        inverted_display_specifier = DataItem.DisplaySpecifier.from_data_item(inverted_data_item)
        inverted_data_item.recompute_data()
        self.assertFalse(inverted_display_specifier.buffered_data_source.is_data_stale)
        self.assertAlmostEqual(inverted_display_specifier.buffered_data_source.data[0, 0], -1.0)
        # now the source data changes and the inverted data needs computing.
        with display_specifier.buffered_data_source.data_ref() as data_ref:
            data_ref.master_data = data_ref.master_data + 2.0
        # verify the actual data values are still stale
        self.assertAlmostEqual(inverted_display_specifier.buffered_data_source.data[0, 0], -1.0)
        # recompute and verify the data values are valid
        inverted_data_item.recompute_data()
        self.assertAlmostEqual(inverted_display_specifier.buffered_data_source.data[0, 0], -3.0)

    def test_statistics_marked_dirty_when_data_changed(self):
        data_item = DataItem.DataItem(numpy.ones((256, 256), numpy.uint32))
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        self.assertTrue(display_specifier.buffered_data_source.is_cached_value_dirty("statistics_data"))
        display_specifier.buffered_data_source.get_processor("statistics").recompute_data(None)
        self.assertIsNotNone(display_specifier.buffered_data_source.get_processed_data("statistics"))
        self.assertFalse(display_specifier.buffered_data_source.is_cached_value_dirty("statistics_data"))
        with display_specifier.buffered_data_source.data_ref() as data_ref:
            data_ref.master_data = data_ref.master_data + 1.0
        self.assertTrue(display_specifier.buffered_data_source.is_cached_value_dirty("statistics_data"))

    def test_statistics_marked_dirty_when_source_data_changed(self):
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.ones((256, 256), numpy.double))
        document_model.append_data_item(data_item)
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        data_item_inverted = DataItem.DataItem()
        invert_operation = Operation.OperationItem("invert-operation")
        invert_operation.add_data_source(data_item._create_test_data_source())
        data_item_inverted.set_operation(invert_operation)
        document_model.append_data_item(data_item_inverted)
        inverted_display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item_inverted)
        inverted_display_specifier.buffered_data_source.get_processor("statistics").recompute_data(None)
        inverted_display_specifier.buffered_data_source.get_processed_data("statistics")
        # here the data should be computed and the statistics should not be dirty
        self.assertFalse(inverted_display_specifier.buffered_data_source.is_cached_value_dirty("statistics_data"))
        # now the source data changes and the inverted data needs computing.
        # the statistics should also be dirty.
        with display_specifier.buffered_data_source.data_ref() as data_ref:
            data_ref.master_data = data_ref.master_data + 1.0
        data_item_inverted.recompute_data()
        self.assertTrue(inverted_display_specifier.buffered_data_source.is_cached_value_dirty("statistics_data"))

    def test_statistics_marked_dirty_when_source_data_recomputed(self):
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.ones((2, 2), numpy.double))
        document_model.append_data_item(data_item)
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        data_item_inverted = DataItem.DataItem()
        invert_operation = Operation.OperationItem("invert-operation")
        invert_operation.add_data_source(data_item._create_test_data_source())
        data_item_inverted.set_operation(invert_operation)
        document_model.append_data_item(data_item_inverted)
        inverted_display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item_inverted)
        inverted_display_specifier.buffered_data_source.get_processor("statistics").recompute_data(None)
        inverted_display_specifier.buffered_data_source.get_processed_data("statistics")
        # here the data should be computed and the statistics should not be dirty
        self.assertFalse(inverted_display_specifier.buffered_data_source.is_cached_value_dirty("statistics_data"))
        # now the source data changes and the inverted data needs computing.
        # the statistics should also be dirty.
        with display_specifier.buffered_data_source.data_ref() as data_ref:
            data_ref.master_data = data_ref.master_data + 2.0
        data_item_inverted.recompute_data()
        self.assertTrue(inverted_display_specifier.buffered_data_source.is_cached_value_dirty("statistics_data"))
        # next recompute data, the statistics should be dirty now.
        data_item_inverted.recompute_data()
        self.assertTrue(inverted_display_specifier.buffered_data_source.is_cached_value_dirty("statistics_data"))
        # get the new statistics and verify they are correct.
        inverted_display_specifier.buffered_data_source.get_processor("statistics").recompute_data(None)
        good_statistics = inverted_display_specifier.buffered_data_source.get_processed_data("statistics")
        self.assertTrue(good_statistics["mean"] == -3.0)

    def test_adding_operation_updates_ordered_operations_list(self):
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.ones((2, 2), numpy.double))
        document_model.append_data_item(data_item)
        data_item_inverted = DataItem.DataItem()
        invert_operation = Operation.OperationItem("invert-operation")
        invert_operation.add_data_source(data_item._create_test_data_source())
        data_item_inverted.set_operation(invert_operation)
        document_model.append_data_item(data_item_inverted)
        # make sure the ordered_operations property returns correct value
        self.assertEqual(data_item_inverted.ordered_operations, [invert_operation])
        # make a binding and make sure it returns correct list
        binding = Binding.ListBinding(data_item_inverted, "ordered_operations")
        self.assertEqual(binding.items, [invert_operation])
        # configure binding. use lists as cheap way around scoping issues.
        removed_index = list()
        inserted_operation_item = list()
        inserted_before_index = list()
        def ordered_operation_removed(index):
            removed_index.append(index)
        def ordered_operation_inserted(operation_item, before_index):
            inserted_operation_item.append(operation_item)
            inserted_before_index.append(before_index)
        binding.remover = ordered_operation_removed
        binding.inserter = ordered_operation_inserted
        data_item_inverted.set_operation(None)
        self.assertEqual(removed_index, [0])
        invert_operation = Operation.OperationItem("invert-operation")
        invert_operation.add_data_source(data_item._create_test_data_source())
        data_item_inverted.set_operation(invert_operation)
        self.assertEqual(inserted_operation_item, [invert_operation])
        self.assertEqual(inserted_before_index, [0])

    def test_modifying_data_item_modified_property_works(self):
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.ones((2, 2), numpy.double))
        document_model.append_data_item(data_item)
        modified = datetime.datetime(2000, 1, 1)
        data_item._set_modified(modified)
        self.assertEqual(data_item.modified, modified)

    def test_modifying_data_item_metadata_updates_modified(self):
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.ones((2, 2), numpy.double))
        document_model.append_data_item(data_item)
        data_item._set_modified(datetime.datetime(2000, 1, 1))
        modified = data_item.modified
        data_item.set_metadata(data_item.metadata)
        self.assertGreater(data_item.modified, modified)

    def test_adding_data_source_updates_modified(self):
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.ones((2, 2), numpy.double))
        document_model.append_data_item(data_item)
        data_item._set_modified(datetime.datetime(2000, 1, 1))
        modified = data_item.modified
        data_item.append_data_source(DataItem.BufferedDataSource())
        self.assertGreater(data_item.modified, modified)

    def test_changing_property_on_display_updates_modified(self):
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.ones((2, 2), numpy.double))
        document_model.append_data_item(data_item)
        data_item._set_modified(datetime.datetime(2000, 1, 1))
        modified = data_item.modified
        data_item.data_sources[0].displays[0].display_calibrated_values = False
        self.assertGreater(data_item.modified, modified)

    def test_changing_data_on_buffered_data_source_updates_modified(self):
        document_model = DocumentModel.DocumentModel()
        data_item = DataItem.DataItem(numpy.ones((2, 2), numpy.double))
        document_model.append_data_item(data_item)
        data_item._set_modified(datetime.datetime(2000, 1, 1))
        modified = data_item.modified
        with data_item.data_sources[0].data_ref() as data_ref:
            data_ref.master_data = numpy.zeros((2, 2))
        self.assertGreater(data_item.modified, modified)

    def test_data_item_with_connected_crop_region_should_not_update_modification_when_subscribed_to(self):
        modified = datetime.datetime(year=2000, month=6, day=30, hour=15, minute=2)
        data_reference_handler = DocumentModel.DataReferenceMemoryHandler()
        document_model = DocumentModel.DocumentModel(data_reference_handler=data_reference_handler)
        data_item = DataItem.DataItem(numpy.ones((16, 16), numpy.uint32))
        document_model.append_data_item(data_item)
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        data_item_cropped = DataItem.DataItem()
        crop_operation = Operation.OperationItem("crop-operation")
        crop_operation.add_data_source(data_item._create_test_data_source())
        data_item_cropped.set_operation(crop_operation)
        crop_operation.establish_associated_region("crop", display_specifier.buffered_data_source)
        document_model.append_data_item(data_item_cropped)
        data_item_cropped.recompute_data()
        data_item._set_modified(modified)
        data_item_cropped._set_modified(modified)
        self.assertEqual(document_model.data_items[0].modified, modified)
        self.assertEqual(document_model.data_items[1].modified, modified)
        def handle_next(x): pass
        data_item.data_sources[0].get_data_and_calibration_publisher().subscribex(Observable.Subscriber(handle_next))
        document_model.recompute_all()
        self.assertEqual(document_model.data_items[0].modified, modified)
        self.assertEqual(document_model.data_items[1].modified, modified)

    def test_data_item_with_operation_with_malformed_values_does_not_changed_when_values_are_updated_with_same_value(self):
        modified = datetime.datetime(year=2000, month=6, day=30, hour=15, minute=2)
        data_reference_handler = DocumentModel.DataReferenceMemoryHandler()
        document_model = DocumentModel.DocumentModel(data_reference_handler=data_reference_handler)
        data_item = DataItem.DataItem(numpy.ones((16, 16), numpy.uint32))
        document_model.append_data_item(data_item)
        display_specifier = DataItem.DisplaySpecifier.from_data_item(data_item)
        data_item_cropped = DataItem.DataItem()
        crop_operation = Operation.OperationItem("crop-operation")
        crop_operation.set_property("bounds", ((0.25, 0.25), (0.5, 0.5)))
        crop_operation.add_data_source(data_item._create_test_data_source())
        data_item_cropped.set_operation(crop_operation)
        crop_operation.establish_associated_region("crop", display_specifier.buffered_data_source)
        document_model.append_data_item(data_item_cropped)
        data_item_cropped.recompute_data()
        data_item._set_modified(modified)
        data_item_cropped._set_modified(modified)
        self.assertEqual(document_model.data_items[0].modified, modified)
        self.assertEqual(document_model.data_items[1].modified, modified)
        crop_operation.set_property("bounds", [[0.25, 0.25], [0.5, 0.5]])
        self.assertEqual(document_model.data_items[0].modified, modified)
        self.assertEqual(document_model.data_items[1].modified, modified)

    # modify property/item/relationship on data source, display, region, etc.
    # copy or snapshot

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.DEBUG)
    unittest.main()
