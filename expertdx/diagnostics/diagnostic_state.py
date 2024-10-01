from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from .diagnostic_item import DiagnosticItem


class DiagnosticState(BaseModel):
    diagnostic_items: List[DiagnosticItem] = Field(default_factory=list)
    causal_relationships: List[Dict] = Field(default_factory=dict)
    cnt: int = Field(default=0)

    def to_dict(self) -> dict:
        return {
            "nodes": [item.to_dict() for item in self.diagnostic_items],
            "edges": self.causal_relationships
        }

    def to_list(self, add_causes: bool = True, add_effects: bool = False, only_not_fixed=False) -> list:
        if only_not_fixed:
            items = [item.to_dict() for item in self.diagnostic_items if not item.is_fixed()]
        else:
            items = [item.to_dict() for item in self.diagnostic_items]

        for item in items:
            if add_causes:
                item["potential_causes"] = list()
            if add_effects:
                item["potential_effects"] = list()

        for rel in self.causal_relationships:
            cause_name = rel["cause"]
            effect_name = rel["effect"]
            description = rel["description"]

            cause_items = [_ for _ in items if _['name'] == cause_name]
            effect_items = [_ for _ in items if _['name'] == effect_name]
            if len(cause_items) > 0 and len(effect_items) > 0:
                cause_item = cause_items[0]
                effect_item = effect_items[0]

                if add_causes is True:
                    effect_item["potential_causes"].append({
                        "name": cause_name,
                        "description": description
                    })
                if add_effects is True:
                    cause_item["potential_effects"].append({
                        "name": effect_name,
                        "description": description
                    })

        return items

    def is_fixed(self):
        return all([item.is_fixed() for item in self.diagnostic_items if item.is_abnormal()])

    def update(self, items: Optional[List[DiagnosticItem]] = None, relationships: Optional[List] = None):
        if items is not None:
            for item in items:
                self.diagnostic_items.append(item)
        if relationships is not None:
            for rel in relationships:
                self.causal_relationships.append(rel)

    def replace(self, old_item: DiagnosticItem, new_items: Optional[List[DiagnosticItem]] = None):
        new = list()
        for item in self.diagnostic_items:
            if item is old_item:
                new.extend(new_items)
            else:
                new.append(item)
        self.diagnostic_items = new
        for rel in self.causal_relationships:
            if rel["cause"] == old_item.name or rel["effect"] == old_item.name:
                self.causal_relationships.remove(rel)

    def get_relationships_by_cause(self, name: str) -> Optional[List]:
        rels = []
        for rel in self.causal_relationships:
            if rel["cause"] == name:
                rels.append(rel)
        return rels

    def get_relationship_by_cause_and_effect(self, cause_name: str, effect_name: str) -> Dict:
        for rel in self.causal_relationships:
            if rel["cause"] == cause_name and rel["effect"] == effect_name:
                return rel
        raise ValueError(f"no cause relationship found: cause_name = {cause_name}, effect_name = {effect_name}")

    def get_item_by_name(self, name: str) -> DiagnosticItem:
        _items = [item for item in self.diagnostic_items if item.name == name]
        assert len(_items) == 1, ValueError(f"more than 1 items with name: {name}")
        return _items[0]

    def get_items_by_attr(
            self,
            product_id_list: Optional[List[int]] = None,
            diagnostic_criteria_type_list: Optional[List[str]] = None,
            diagnostic_criteria_subtype_list: Optional[List[str]] = None,
            severity_status_list: Optional[List[int]] = None
    ) -> List[DiagnosticItem]:
        _items = self.diagnostic_items.copy()
        if product_id_list:
            _items = [item for item in _items if item.product.value in product_id_list]
        if diagnostic_criteria_type_list:
            _items = [item for item in _items if item.diagnostic_criteria.type in diagnostic_criteria_type_list]
        if diagnostic_criteria_subtype_list:
            _items = [item for item in _items if item.diagnostic_criteria.subtype in diagnostic_criteria_subtype_list]
        if severity_status_list:
            _items = [item for item in _items if item.severity.value in severity_status_list]
        return _items


def update_item_name(item: DiagnosticItem, state: DiagnosticState, new_name):
    causal_relationships = state.get_relationships_by_cause(item.name)
    for rel in causal_relationships:
        rel["cause"] = new_name
    item.name = new_name

