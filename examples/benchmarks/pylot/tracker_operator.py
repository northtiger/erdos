import cv2
from cv_bridge import CvBridge

from erdos.data_stream import DataStream
from erdos.message import Message
from erdos.op import Op
from erdos.utils import setup_logging
import pylot_utils


class TrackerOperator(Op):
    def __init__(self, name, min_runtime_us=None, max_runtime_us=None):
        super(TrackerOperator, self).__init__(name)
        self._logger = setup_logging(self.name, 'pylot.log')
        self._min_runtime = min_runtime_us
        self._max_runtime = max_runtime_us
        self._bridge = CvBridge()
        self._bounding_box = None

    @staticmethod
    def setup_streams(input_streams, op_name):
        def is_rgb_camera_stream(stream):
            return stream.labels.get('camera_type', '') == 'RGB'

        def is_detector_stream(stream):
            return stream.labels.get('detector', '') == 'true'

        input_streams.filter(is_rgb_camera_stream) \
                     .add_callback(TrackerOperator.on_frame)
        input_streams.filter(is_detector_stream) \
                     .add_callback(TrackerOperator.on_bounding_box)
        # TODO(ionel): Specify output stream type
        return [DataStream(name='{}_output'.format(op_name))]

    def on_bounding_box(self, msg):
        self._logger.info('%s received detected object at time %s', self.name,
                          msg.timestamp)
        self._bounding_box = msg.data

    def on_frame(self, msg):
        self._logger.info('%s received frame %s', self.name, msg.timestamp)
        cv_img = self._bridge.imgmsg_to_cv2(msg.data, "bgr8")
        pylot_utils.do_work(self._logger, self._min_runtime, self._max_runtime)
        bboxes = pylot_utils.generate_synthetic_bounding_boxes(1, 1)
        self._logger.info('%s published bounding boxes %s', self.name,
                          msg.timestamp)
        output_msg = Message(bboxes, msg.timestamp)
        output_name = '{}_output'.format(self.name)
        self.get_output_stream(output_name).send(output_msg)

    def execute(self):
        self._logger.info('Executing %s', self.name)
        self.spin()
