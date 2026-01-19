## TODO everything but components are sorted... optimizations of access, removal, and insertion may be available!

class Scene:
    def __init__(self):
        self._entities = list()
        self._next_id = 0

    def spawn(self) -> Entity:
        """Creates a new entity, and adds it to the scene."""
        return Entity(self)

    def issue_new_entity_id(self, entity):
        """Initializes a new entity's id in this scene."""
        entity._id = self._next_id
        # Improves insertion performance to simply increment the IDs.
        # New entities are inserted at the end of the list, and stay sorted by ID!
        self._next_id += 1

    def get_entity_by_id(self, entity_id) -> Entity | None:
        for entity in self._entities:
            if entity.id == entity_id:
                return entity
        return None

    def add_entity(self, entity: Entity):
        self._entities.append(entity)
        # self._entities.sort(key=lambda e: e.id)      # NOTE: I REALLY want to guarantee that it's sorted.

    def remove_entity(self, entity: Entity):
        self._entities.remove(entity)



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
        return succeeds

    def try_detach(self, component) -> bool:
        succeeds = self.has_specific_component(component)
        if succeeds:
            self._components[type(component)].remove(component)
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



class Component:
    def __init__(self, parent:Entity|None):
        self._parent:Entity|None = parent
        self.search_tag:type[Component] = type(self)
        ## TODO does this select the most specific applicable type?
        ## TODO does this work robustly with entity searching? See all instances of "type()"

    def try_get_parent(self) -> Entity|None:
        return self._parent

    def on_attach(self):
        pass

    def on_detach(self):
        pass



class System:
    def __init__(self, function:Callable):
        self._function:Callable = function

    ## TODO subscribe to CritScript system calling!

    def invoke(self, scene_ctx:Scene, *args, **kwargs):
        return self.function(scene_ctx, *args, **kwargs)