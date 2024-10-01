import logging
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Union


# anonymous product
class Product(int, Enum):
    SPARK = 4
    SUPERSQL = 5
    US = 6
    YARN = 7
    HDFS = 9
    IDEX = 16
    MAPREDUCE = 19
    THIVE = 23
    OTHER = 0


class Severity(int, Enum):
    UNKNOWN = -1
    NORMAL = 0
    MINOR = 1
    MAJOR = 2
    CRITICAL = 3

    def is_normal(self):
        return self == self.NORMAL

    def is_abnormal(self):
        return self in [self.MAJOR, self.MINOR, self.CRITICAL]

    def is_unknown(self):
        return self == self.UNKNOWN


class DiagnosisType(str, Enum):
    RULE = 'rule'
    LOG = 'log'
    CODE = 'code'
    MIX = 'mix'


class DiagnosticCriteria(BaseModel):
    name: str
    type: DiagnosisType
    subtype: Optional[str]
    description: Optional[str]

    def display(self):
        return {
            "type": self.type,
            "subtype": self.subtype,
            "name": self.name,
            "description": self.description
        }


class DiagnosticItem(BaseModel):
    name: str = Field(default_factory=str)
    product: Product = Field(default=Product.SPARK)
    severity: Severity = Field(default=Severity.UNKNOWN)

    symptom: Optional[str] = Field(default=None)
    expert_suggests: Optional[str] = Field(default=None)
    expert_analysis: Optional[str] = Field(default=None)
    diagnostic_criteria: Optional[DiagnosticCriteria] = Field(default=None)

    fixed: bool = Field(default=False)
    possible_root_cause: int = Field(default=1)

    def is_suspect(self) -> bool:
        return self.severity.is_unknown()

    def is_normal(self) -> bool:
        return self.severity.is_normal()

    def is_abnormal(self) -> bool:
        return self.severity.is_abnormal()

    def is_fixed(self) -> bool:
        return self.fixed is True

    def is_possible_root_cause(self) -> bool:
        if self.possible_root_cause == 0:
            return False
        elif self.possible_root_cause == 1:
            return True
        else:
            raise ValueError(f"Not been verified.")

    def to_dict(self, add_fixed=False) -> dict:
        item_display = {
            "name": self.name,
            "product": self.product.name.lower(),
            "severity": self.severity.name.lower(),
            "symptom": self.symptom,
            "expert_suggests": self.expert_suggests,
            "expert_analysis": self.expert_analysis,
            "diagnostic_criteria": self.diagnostic_criteria.display() if self.diagnostic_criteria else None
        }
        if add_fixed:
            item_display["fixed"] = self.is_fixed()

        return item_display

    @staticmethod
    def from_dict(nodes: List[Dict]):
        items = []
        for node in nodes:
            item = create_diagnostic_item(
                name=node["name"],
                product_id=product_name2id(node["product"]),
                diagnostic_criteria_type='rule',
                diagnostic_criteria_subtype=node["diagnostic_criteria"]["subtype"],
                diagnostic_criteria_name=node["diagnostic_criteria"]["name"],
                diagnostic_criteria_description=node["diagnostic_criteria"]["description"],
                symptom=node["symptom"],
                severity_status=severity_name2status(node["severity"]),
                expert_suggests=node["expert_suggests"],
                expert_analysis=node["expert_analysis"]
            )
            items.append(item)
        return items

    def set_possible_root_cause(self, possible_root: bool) -> None:
        if possible_root is True:
            self.possible_root_cause = 1
        else:
            self.possible_root_cause = 0

    def set_fixed(self):
        self.fixed = True

    def set_normal(self):
        self.severity = Severity.NORMAL

    def set_abnormal(self, severity_status: int = 2):
        self.severity = Severity(severity_status)


def create_diagnostic_item(
        name: str,
        product_id: int,
        severity_status: int = 0,
        symptom: Optional[str] = "",
        expert_suggests: Optional[str] = "",
        expert_analysis: Optional[str] = "",
        diagnostic_criteria_type: Optional[str] = None,
        diagnostic_criteria_subtype: Optional[str] = None,
        diagnostic_criteria_name: Optional[str] = None,
        diagnostic_criteria_description: Optional[str] = None,
        expand: bool = Field(default=False)
):
    try:
        product = Product(product_id)
    except ValueError as e:
        raise ValueError(f"invalid product_id: {e}")

    try:
        severity = Severity(severity_status)
    except ValueError as e:
        raise ValueError(f"invalid severity_id: {e}")

    # init suspected DiagnosticItem
    if expand is True:
        item = DiagnosticItem(
            name=name,
            product=product,
            severity=severity,
            expert_suggests=expert_suggests,
            expert_analysis=expert_analysis,
        )
        return item

    if diagnostic_criteria_type:
        try:
            diagnosis_type = DiagnosisType(diagnostic_criteria_type)
        except ValueError as e:
            raise ValueError(f"valid diagnosis_type: [rule, log, code]: {e}")

        criteria = DiagnosticCriteria(
            type=diagnosis_type,
            subtype=diagnostic_criteria_subtype,
            name=diagnostic_criteria_name,
            description=diagnostic_criteria_description
        )
    else:
        assert severity.is_unknown()
        criteria = None

    # init detected DiagnosticItem
    item = DiagnosticItem(
        name=name,
        product=product,
        severity=severity,
        symptom=symptom,
        expert_suggests=expert_suggests,
        expert_analysis=expert_analysis,
        diagnostic_criteria=criteria,
    )
    return item


def create_diagnostic_criteria(
        criteria_name: str,
        criteria_type: str,
        criteria_subtype: Optional[str],
        criteria_description: Optional[str]):
    if criteria_type == 'log':
        criteria_type = DiagnosisType.LOG
    elif criteria_type == 'code':
        criteria_type = DiagnosisType.CODE
    elif criteria_type == 'rule':
        criteria_type = DiagnosisType.RULE
    else:
        criteria_type = DiagnosisType.MIX

    criteria = DiagnosticCriteria(
        name=criteria_name,
        type=criteria_type,
        subtype=criteria_subtype,
        description=criteria_description
    )
    return criteria


def product_id2name(product_id: Union[int, str]) -> str:
    if isinstance(product_id, str):
        product_id = int(product_id)
    try:
        return Product(product_id).name
    except ValueError:
        raise ValueError(f"invalid product_id: {product_id}")


def product_name2id(product_name: str) -> int:
    try:
        return Product[product_name.upper()].value
    except KeyError:
        logging.warning(f"invalid product_name: {product_name}")
        return Product.OTHER.value


def severity_status2name(severity_status: Union[int, str]) -> str:
    if isinstance(severity_status, str):
        severity_status = int(severity_status)
    try:
        return Severity(severity_status).name
    except ValueError:
        raise ValueError(f"invalid severity_id: {severity_status}")


def severity_name2status(severity_name: str) -> int:
    try:
        return Severity[severity_name.upper()].value
    except ValueError:
        raise ValueError(f"invalid severity_name: {severity_name.upper()}")
