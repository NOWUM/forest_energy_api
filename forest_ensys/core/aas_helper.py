import requests
import json
from typing import Dict, Any, Optional, Generator, List

from aas_core3 import jsonization
from aas_core3.types import (
    SubmodelElementCollection,
    Property,
    Range,
    SubmodelElement,
)

needed_properties = [
    "powerMax",
    "regenerationDuration",
    "from",
    "until",
    "activationGradient",
    "deactivationGradient",
    "electricityNetworkFee",
    "co2Price",
    "gasPrice",
]

class ServerEasyv3:
    @staticmethod
    def submodels_server_url() -> str:
        return "https://forest.nowum.fh-aachen.de/aas-env/submodels"

    def send_request_helper(self, url: str) -> Optional[requests.Response]:
        try:
            response = requests.get(url, timeout=3)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None

    def get_submodel(self, submodel_id: str) -> Optional[Any]:
        url = f"{self.submodels_server_url()}/{submodel_id}"
        response = self.send_request_helper(url)
        if response is None:
            return None

        try:
            json_data = response.json()
            submodel = jsonization.submodel_from_jsonable(json_data)
            print("Deserialization successful:")
            print(submodel)
            return submodel
        except json.JSONDecodeError as e:
            print(f"JSON decode failed: {e}")
            return None
        except jsonization.DeserializationException as ex:
            print(f"Deserialization failed: {ex}")
            return None

def traverse_elements(element: SubmodelElement) -> Generator[Dict[str, Any], None, None]:
    if isinstance(element, SubmodelElementCollection):
        if hasattr(element, 'value'):
            for sub_element in element.value:
                yield from traverse_elements(sub_element)
    elif isinstance(element, (Property, Range)):
        if element.id_short in needed_properties:
            value = getattr(element, "value", None)
            min_value = getattr(element, "min", None)
            max_value = getattr(element, "max", None)
            kind_value = getattr(getattr(element, "kind", None), "value", None) if hasattr(element, "kind") else None

            qualifier_values = [q.value for q in element.qualifiers] if hasattr(element, "qualifiers") and element.qualifiers else []
            qualifier_types = [q.type for q in element.qualifiers] if hasattr(element, "qualifiers") and element.qualifiers else []
            if value is None and min_value is None and max_value is None:
                return
            yield {
                "idShort": element.id_short,
                "value": value if value is not None else max_value,
                "qualifier_values": qualifier_values,
                "qualifier_types": qualifier_types,
            }

def get_data_from_aas() -> Dict[str, Any]:
    server = ServerEasyv3()
    submodel_id = "aHR0cHM6Ly9hZG1pbi1zaGVsbC5pby9pZHRhL0VuZXJneUZsZXhpYmlsaXR5RGF0YU1vZGVsLzEvMC9FbmVyZ3lGbGV4aWJpbGl0eURhdGFNb2RlbA"
    submodel = server.get_submodel(submodel_id)

    return_dict = {}
    if submodel and hasattr(submodel, "submodel_elements") and submodel.submodel_elements:
        print("Submodel elements found.")
        for element in submodel.submodel_elements:
            for elem_data in traverse_elements(element):
                return_dict[elem_data["idShort"]] = elem_data["value"]
    return return_dict

if __name__ == "__main__":
    print(get_data_from_aas())
