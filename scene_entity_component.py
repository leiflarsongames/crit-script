

class Scene:
    def __init__(self):
        self.entities = list()
        next_id = 0

    def get_new_entity_id(self):
        return_value = next_id
        # TODO issuing consecutive IDs is intended to enable object pools to improve performance by preserving
        # spatial locality. In our case, does this actually make a performance impact?
        next_id += 1                # update next_id
        return return_value         # return what next_id originally was

    def get_entity_by_id(self, entity_id) -> Entity | None:
        for entity in self.entities:
            if entity.id == entity_id:
                return entity
        return None

    def add_entity(self, entity: Entity):
        self.entities.append(entity)
        self.entities.sort(key=lambda e: e.id)      # NOTE: This isn't even necessary, but I REALLY want to guarantee that it's sorted. TODO update with optimization by removing sorting if at all necessary. Just- insert it into the correct spot?

    def remove_entity(self, entity: Entity):
        self.entities.remove(entity)

class Entity:
    def __init__(self, scene_context:Scene):
        self.id = scene_context.get_new_entity_id()
        scene_context.add_entity(self)
class Component:
    def __init__(self, parent:Entity, search_tag:type[Component]):
        self.parent:Entity = parent
        self.search_tag:type[Component] = search_tag

