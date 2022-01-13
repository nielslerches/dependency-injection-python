from abc import ABC
from dataclasses import dataclass
from graphlib import TopologicalSorter
from typing import NewType, get_type_hints

RedisURI = NewType("RedisURI", str)


class DependencyContainer(ABC):
    def __init__(self, **kwargs):
        cls = self.get_type()

        root_values = kwargs.copy()
        root_values.update(self.get_defaults())

        root_type_hints = get_type_hints(cls)
        root_type_hints_inverted = {
            value: key for key, value in root_type_hints.items()
        }

        ready_objects = {
            type_hint: root_values[key]
            for key, type_hint in root_type_hints.items()
            if key in root_values
        }

        sorter = TopologicalSorter(self.get_type_graph(cls))
        sorter.prepare()

        while sorter.is_active():
            ready_types = sorter.get_ready()
            for ready_type in ready_types:
                if ready_type is cls or ready_type in ready_objects:
                    sorter.done(ready_type)
                    break
                type_hints = get_type_hints(ready_type)
                kwargs = {
                    key: ready_objects.get(
                        type_hint, root_values[root_type_hints_inverted[type_hint]]
                    )
                    for key, type_hint in type_hints.items()
                }
                ready_obj = ready_type(**kwargs)
                ready_objects[ready_type] = ready_obj
                sorter.done(ready_type)

        for key, type_hint in root_type_hints.items():
            setattr(self, key, ready_objects[type_hint])

    def get_type(self):
        return type(self)

    def get_defaults(self):
        return {
            key: value
            for key, value in vars(self.get_type()).items()
            if not (key.startswith("__") and key.startswith("__"))
        }

    def get_type_graph(self, typ: type):
        type_hints = get_type_hints(typ)
        types_required = list(type_hints.values())
        type_graph = {typ: types_required}
        for type_required in types_required:
            type_graph.update(self.get_type_graph(type_required))
        return type_graph


@dataclass
class RedisClient:
    redis_uri: RedisURI


class Config(DependencyContainer):
    redis_client: RedisClient
    redis_uri: RedisURI = "localhost:6379"


config = Config()
print(config.redis_client)
