import typing


_KT = typing.TypeVar("_KT")
_VT = typing.TypeVar("_VT")


class Map(dict, typing.Mapping[_KT, _VT]):
    """
    Example:
    m = Map({'first_name': 'Eduardo'}, last_name='Pool', age=24, sports=['Soccer'])
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update(*args, **kwargs)

    def __getattr__(self, attr: _KT) -> typing.Optional[_VT]:
        return self.get(attr)

    def __setattr__(self, key: _KT, value: _VT):
        self.__setitem__(key, value)

    def __setitem__(self, key: _KT, value: _VT):
        super(Map, self).__setitem__(key, value)
        self.__dict__.update({key: value})

    def __delattr__(self, item):
        self.__delitem__(item)

    def __delitem__(self, key: _KT):
        super(Map, self).__delitem__(key)
        del self.__dict__[key]
