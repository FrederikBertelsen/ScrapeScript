from typing import Optional, Union

class Selector:
    """
    Represents a CSS selector that can be chained to represent nested element queries.
    When parent is provided, first find elements matching the parent selector,
    then find children within those elements using this selector's css_selector.
    """
    def __init__(
        self, 
        css_selector: Optional[str],
        parent: Optional['Selector'] = None,
        index: Optional[int] = None
    ):
        self.css_selector = css_selector  # The CSS selector text
        self.parent = parent              # Parent selector if this is a nested query
        self.index = index                # Index to use if selecting from a list