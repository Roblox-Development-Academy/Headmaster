def parameters(*args, **kwargs):
    return args, kwargs


def unpack(packed_parameters, coroutine):
    return coroutine(*packed_parameters[0], **packed_parameters[1])
