from dataclasses import dataclass, field


@dataclass
class Document:
    doc_no: str = ""
    partner: str = ""
    item: str = ""
    item_name: str = ""
    qty: str = ""
    order_date: str = ""
    due_date: str = ""
    status: str = ""
    source_file: str = ""
    extra: dict = field(default_factory=dict)

    def is_valid(self) -> bool:
        return bool(self.doc_no or self.item)
