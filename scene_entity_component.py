## TODO everything but components are sorted... optimizations of access, removal, and insertion may be available!

from crit_script import make_crit_script_identifier, crit_script
from dataclasses import dataclass

_current_scene:Scene|None = None
_component_traits:dict[str, ComponentTrait] = dict()

class Scene:
    """Singleton"""
    def __init__(self):
        self._entities:list[Entity] = []
        self._entities = list()
        self._next_id = 0

    @classmethod
    def get(cls):
        if _current_scene:
            _current_scene = Scene()
        else:
            return _current_scene

    # @classmethod
    # def tear_down(cls):
    #     self = cls.get()
    #     for entity in self._entities:

    def spawn(self) -> Entity:
        """Creates a new entity, and adds it to the scene."""
        return Entity(self)

    def issue_new_entity_id(self, entity):
        """Initializes a new entity's id in this scene."""
        entity._id = self._next_id
        # Improves insertion performance to simply increment the IDs.
        # New entities are inserted at the end of the list, and stay sorted by ID!
        self._next_id += 1

    def get_entity_by_id(self, entity_id:int) -> Entity | None:
        for entity in self._entities:
            if entity.id == entity_id:
                return entity
        return None

    def add_entity(self, entity: Entity):
        self._entities.append(entity)
        # self._entities.sort(key=lambda e: e.id)      # NOTE: I REALLY want to guarantee that it's sorted.

    def remove_entity(self, entity: Entity):
        self._entities.remove(entity)




# Note: Encourage the user to do as MUCH AS POSSIBLE with an entity through components!!!
# A scene's job is to hold entities
# An entity's job is to hold components
# A component's job is to hold data and do behavior sparingly
# A system's job is to give components behavior in the game loop
class Entity:
    def __init__(self, scene_context:Scene):
        scene_context.issue_new_entity_id(self)     # assigns self._id
        scene_context.add_entity(self)
        self._components:dict[type[Component], list[Component]] = dict()

    def try_attach(self, component) -> bool:
        """Attaches a component to this entity, if it is not already attached to this entity.

        Returns whether the operation did anything."""
        succeeds = not self.has_specific_component(components)
        if succeeds:
            self._components[type(component)].append(component)
            component._update_my_attach(self)
        return succeeds

    def try_detach(self, component) -> bool:
        succeeds = self.has_specific_component(component)
        if succeeds:
            self._components[type(component)].remove(component)
            component._update_my_detach()
        return succeeds

    def attach(self, component) -> Entity:
        try_attach(component)
        return Entity

    def detach(self, component) -> Entity:
        try_detach(component)
        return Entity

    def get_all_components(self) -> list[Component]:
        return list(itertools.chain.from_iterable(self._components.values()))

    def has_components_of_type(self, type:type[Component]) -> bool:
        return self._components[type] is not None

    def try_get_component_of_type(self, type:type[Component]) -> Component | None:
        if self.has_components_of_type(type):
            return self._components[type][0]
        else:
            return None

    def try_get_all_components_of_type(self, type:type[Component]) -> list[Component] | None:
        if self.has_components_of_type(type):
            return self._components[type]
        else:
            return None

    def has_specific_component(self, component:Component):
        # TODO This better work with specifically an IDENTICAL copy of it...
        # TODO is the reference being passed in and the reference retained in self._components the same reference?
        if self.has_components_of_type(type(component)):
            return component in self._components[type(component)]

    def get_id(self) -> int:
        return self._id

    def get_all_component_types(self) -> list[type[Component]]:
        return self._conponents.keys()

@dataclass
class ComponentTrait:
    """A template which specifies which properties are to be expected from a component.
    Traits may be mixed together. Any properties that are present in two traits will be considered part of both
    traits."""
    def __init__(self, name:str, variables:dict[str, Any]):
        self.name:str = name
        self.variables:dict[str, Any] = variables       # identifier, default value

    # def submit_component_trait(self):
    #
    #
    # def submit_variable(self, key: str, starting_value: Any | None = None):
    #     """Adds a variable as a valid option to this component, and submits it as a function if it does not already
    #     exist."""
    #     self.data[key] = starting_value
    #     ## have this submit functions to CritScript manipulating this variable!
    #
    #
    #
    #     # TODO submit getter
    #     @crit_script(
    #         inputs=Pin("component", Component),
    #         outputs=Pin("value"),
    #         category=f"{self.name}",
    #         custom_name=f"get-{key}",
    #         ## TODO make a just-in-time node!
    #     )
    #     def get_property_from_trait(component:Component) -> Any:
    #         return component.data[key]
    #
    #     # TODO submit setter
    #     @crit_script(
    #         inputs=(Pin("component", Component), ),
    #         outputs=Pin("value"),
    #         category=f"{self.name}",
    #         custom_name=f"set-{key}",
    #     )
    #     def get_property_from_trait(component: Component, value:Any) -> Any:
    #         return component.data[key]



class Component:
    def __init__(self, traits:list[ComponentTrait]):
        self._parent:Entity|None = parent
        self._traits:list[ComponentTrait] = list()
        self.data:dict[str, Any] = dict()
        ## TODO does this select the most specific applicable type?
        ## TODO does this work robustly with entity searching? See all instances of "type()"

    def try_get_parent(self) -> Entity|None:
        return self._parent

    def _update_my_attach(self, entity:Entity):
        self._parent = entity
        self.on_attach()

    def _update_my_detach(self):
        if self._parent is not None:
            self._parent.on_detach()
            self._parent = None

    def on_attach(self):
        pass

    def on_detach(self):
        pass

    def get(self, key:str) -> Any:
        if key in self.data:
            return self.data[key]
        else:
            raise KeyError(f"Component {self} has no variable named {key}!")

    def set(self, key:str, value:Any) -> bool:
        if key in self.data:
            self.data[key] = value
        else:
            raise KeyError(f"Component {self} has no variable named {key}!")

    def has_variable(self, key:str) -> bool:
        return key in self.data

    def variable_is_valid(self, key:str) -> bool:
        return key in self.data and self.data[key] is not None


class System:
    def __init__(self, function:Callable):
        self._function:Callable = function

    ## TODO subscribe to CritScript system calling!

    def invoke(self, scene_ctx:Scene, *args, **kwargs):
        return self.function(scene_ctx, *args, **kwargs)