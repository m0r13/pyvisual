from collections import namedtuple
import numpy as np

# keep_value_on_disconnect: whether to take over the connected value into the manual value
#   when a connection from one node to another is removed
# basically set this to true for all directly editable data types (numeric, str, vec2, ...)
BaseType = namedtuple("BaseDType", ["name", "serialize", "unserialize", "keep_value_on_disconnect"])

def dummy_serializer():
    def serialize(value):
        return ""
    def unserialize(json_data):
        return None
    return serialize, unserialize

def numpy_serializer(dtype=np.float32):
    def serialize(value):
        # TODO
        # errors happened here, somewhere there is a list instead of a numpy array
        # probably some manual or default value of some port
        if isinstance(value, list):
            return value
        return value.tolist()
    def unserialize(json_data):
        return np.array(json_data, dtype=dtype)
    return serialize, unserialize

def float_serializer():
    # backup original python float type!
    _float = float
    # it seemed to happen somehow that some value was of type 'bool_'
    # sooo just make it a float just in case
    def serialize(value):
        return _float(value)
    def unserialize(json_value):
        return _float(json_value)
    return serialize, unserialize

base_float = BaseType("float", *float_serializer(), True)
base_str = BaseType("str", lambda value: value, lambda json_value: json_value, True)
base_vec2 = BaseType("vec2", *numpy_serializer(), True)
base_vec4 = BaseType("vec4", *numpy_serializer(), True)
base_mat4 = BaseType("mat4", *numpy_serializer(), False)
base_tex2d = BaseType("tex2d", *dummy_serializer(), False)
base_ssbo = BaseType("ssbo", *dummy_serializer(), False)
base_audio = BaseType("audio", *dummy_serializer(), False)
base_midi = BaseType("midi", *dummy_serializer(), False)
base_fft = BaseType("fft", *dummy_serializer(), False)

Type = namedtuple("DType", ["name", "base_type", "default"])

bool = Type("bool", base_float, lambda: 0.0)
event = Type("event", base_float, lambda: 0.0)
int = Type("int", base_float, lambda: 0.0)
float = Type("float", base_float, lambda: 0.0)
str = Type("str", base_str, lambda: "")
assetpath = Type("assetpath", base_str, lambda: "")
vec2 = Type("vec2", base_vec2, lambda: np.array([0.0, 0.0], dtype=np.float32))
color = Type("color", base_vec4, lambda: np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32))
mat4 = Type("mat4", base_mat4, lambda: np.eye(4, dtype=np.float32))
tex2d = Type("tex2d", base_tex2d, lambda: None)
ssbo = Type("ssbo", base_ssbo, lambda: None)
audio = Type("audio", base_audio, lambda: None)
midi = Type("midi", base_midi, lambda: [])
fft = Type("fft", base_fft, lambda: None)

dtypes = {}
for dtype in (bool, event, int, float, str, assetpath, vec2, color, mat4, tex2d, ssbo, audio, midi, fft):
    dtypes[dtype.name] = dtype

