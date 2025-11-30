"""
Page Parser module for AI agent browser interactions
Converted from TypeScript to Python using SeleniumBase Driver
Based on the example SeleniumBase implementation
"""

import logging
from typing import Dict, Any, List, Optional, Union, Tuple
from pydantic import BaseModel, Field
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import StaleElementReferenceException
from seleniumbase import Driver

# Configure a logger for this module
logger = logging.getLogger(__name__)


class ElementAttributes(BaseModel):
    """Represents the HTML attributes of an element"""
    id: str = Field(default="", description="The element's ID attribute")
    aria_label: str = Field(default="", alias="aria-label", description="The element's aria-label attribute")
    placeholder: str = Field(default="", description="The element's placeholder attribute")
    class_name: str = Field(default="", alias="class", description="The element's class attribute")
    value: str = Field(default="", description="The element's value attribute")
    name: str = Field(default="", description="The element's name attribute")
    type: str = Field(default="", description="The element's type attribute")
    href: str = Field(default="", description="The element's href attribute (for links)")
    title: str = Field(default="", description="The element's title attribute")
    disabled: bool = Field(default=False, description="Whether the element is disabled")


class PageElement(BaseModel):
    """Represents a single element on the page with all its relevant information."""
    ref: str = Field(..., description="A unique, temporary reference ID for this element for the current page view.")
    tag: str = Field(..., description="The HTML tag name of the element")
    text: str = Field(default="", description="The text content of the element")
    children_text: str = Field(default="", description="Text content from child elements when element has no direct text")
    attributes: ElementAttributes = Field(default_factory=ElementAttributes, description="The element's HTML attributes")
    is_interactive: bool = Field(..., description="Whether the element is interactive")
    css_selector: str = Field(..., description="CSS selector to uniquely identify this element")
    index: int = Field(..., description="Sequential index for this element")
    internal_selector: Optional[str] = Field(None, description="Internal selector for interactive elements (legacy)")
    data_attributes: Dict[str, str] = Field(default_factory=dict, description="All data-* attributes on the element")
    table_cells: List[Dict[str, str]] = Field(default_factory=list, description="For TR elements, contains info about TD/TH children")

    # Legacy compatibility properties
    @property
    def id(self) -> Optional[str]:
        return self.attributes.id if self.attributes.id else None
    
    @property
    def type(self) -> str:
        return self.tag
    
    @property
    def class_name(self) -> Optional[str]:
        return self.attributes.class_name if self.attributes.class_name else None
    
    @property
    def selector(self) -> str:
        return self.css_selector
    
    @property
    def text_content(self) -> str:
        return self.text
    
    @property
    def value(self) -> Optional[str]:
        return self.attributes.value if self.attributes.value else None
    
    @property
    def placeholder(self) -> Optional[str]:
        return self.attributes.placeholder if self.attributes.placeholder else None
    
    @property
    def disabled(self) -> Optional[bool]:
        return self.attributes.disabled
    
    @property
    def input_type(self) -> Optional[str]:
        return self.attributes.type if self.attributes.type else None
    
    @property
    def href(self) -> Optional[str]:
        return None  # Would need to be added to attributes if needed
    
    @property
    def target(self) -> Optional[str]:
        return None  # Would need to be added to attributes if needed
    
    @property
    def src(self) -> Optional[str]:
        return self.attributes.get('src')
    
    @property
    def alt(self) -> Optional[str]:
        return self.attributes.get('alt')


# Define a type hint for our structured element data for clarity
ElementInfoList = List[PageElement]


class PageParser:
    """
    Parses a webpage using native SeleniumBase methods to create a structured,
    agent-readable representation of the page's content and interactive elements.
    """

    def __init__(self, driver: Driver):
        """
        Initializes the parser with a SeleniumBase driver instance.

        Args:
            driver: An active SeleniumBase Driver instance.
        """
        self.driver = driver
        
        # Tags we want to extract for context (static content)
        self.STATIC_TAGS = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'th', 'td', 'tr', 'table', 'label', 'caption', 'span', 'strong', 'b', 'em', 'i', 'u', 'small', 'mark', 'dl', 'dt', 'dd', 'img']
        
        # Tags that are inherently interactive
        self.INTERACTIVE_TAGS = ['a', 'button', 'input', 'select', 'textarea']
        
        # Additional attributes or roles that signify interactivity
        self.INTERACTIVE_ATTRIBUTES = ['[onclick]', '[role="button"]', '[role="link"]', '[role="checkbox"]', '[role="tab"]', '[contenteditable="true"]']
        
        # Comprehensive content tags for content mapping (includes more elements)
        self.CONTENT_TAGS = [
            'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'th', 'td', 'tr', 'table', 'label', 'caption',
            'a', 'button', 'input', 'select', 'textarea', 'span', 'div', 'article', 'section',
            'header', 'footer', 'nav', 'aside', 'main', 'figure', 'figcaption', 'blockquote',
            'pre', 'code', 'strong', 'em', 'b', 'i', 'u', 'small', 'mark', 'del', 'ins',
            'sub', 'sup', 'time', 'address', 'cite', 'abbr', 'dfn', 'kbd', 'samp', 'var',
            'dl', 'dt', 'dd', 'img'
        ]

    def get_page_maps(self, map_type: str = "lean") -> Tuple[ElementInfoList, str, ElementInfoList, str]:
        """
        Generate both interactive and content maps in a single call.
        
        Args:
            map_type: "rich" for full CSS selectors, "lean" for ref-based format
        
        Returns:
            A tuple containing:
            - interactive_elements: List of PageElement objects for interactive elements
            - interactive_string: Formatted string for interactive elements
            - content_elements: List of PageElement objects for content elements  
            - content_string: Formatted string for content elements
        """
        logger.info(f"Starting unified page map generation with map_type: {map_type}...")
        
        # Clean up any existing markers first
        self._cleanup_interactive_markers()
        self._cleanup_content_markers()
        
        # Get all elements once
        all_elements = self._build_unified_element_map()
        
        # Split into interactive and content
        interactive_elements = [elem for elem in all_elements if elem.is_interactive]
        content_elements = [elem for elem in all_elements if not elem.is_interactive]
        
        # Format both maps using the simplified functions
        interactive_string = self._format_interactive_map_for_prompt(interactive_elements, map_type)
        content_string = self._format_content_map_for_prompt(content_elements, map_type)
        
        logger.info(f"Unified page map complete. Found {len(interactive_elements)} interactive and {len(content_elements)} content elements.")
        
        return interactive_elements, interactive_string, content_elements, content_string



    def _build_unified_element_map(self) -> ElementInfoList:
        """
        Builds a unified element map using JavaScript-processed element data.
        This eliminates all Python-Selenium communication overhead.
        """
        # Get all processed element data from JavaScript
        element_data_list = self._collect_and_process_elements()
        
        # Convert JavaScript data to PageElement objects
        unified_elements: ElementInfoList = []
        unified_index_counter = 0

        for element_data in element_data_list:
            try:
                # Build the attributes object from JavaScript data
                attributes = ElementAttributes(
                    id=element_data['attributes']['id'],
                    **{"aria-label": element_data['attributes']['aria-label']},
                    placeholder=element_data['attributes']['placeholder'],
                    **{"class": element_data['attributes']['class']},
                    value=element_data['attributes']['value'],
                    name=element_data['attributes']['name'],
                    type=element_data['attributes']['type'],
                    href=element_data['attributes']['href'],
                    title=element_data['attributes']['title'],
                    disabled=element_data['attributes']['disabled']
                )

                # Determine text length based on element type
                text_length = 250 if element_data['is_interactive'] else 500
                truncated_text = element_data['text'][:text_length] if element_data['text'] else ""
                
                # Handle children_text for interactive elements without direct text
                children_text = element_data.get('children_text', '')
                if children_text:
                    children_text = children_text[:200]  # Limit children_text length

                # Get data attributes (default to empty dict if not present)
                data_attrs = element_data.get('data_attributes', {})

                # Get table cells for TR elements (default to empty list if not present)
                table_cells = element_data.get('table_cells', [])

                # Create the PageElement
                page_element = PageElement(
                    ref=str(element_data['ref']),  # Parse the ref (cast to string for safety)
                    tag=element_data['tag'],
                    text=truncated_text,
                    children_text=children_text,
                    attributes=attributes,
                    is_interactive=element_data['is_interactive'],
                    css_selector=element_data['css_selector'],
                    index=unified_index_counter,
                    data_attributes=data_attrs,
                    table_cells=table_cells
                )

                unified_elements.append(page_element)
                unified_index_counter += 1

            except Exception as e:
                logger.warning(f"Failed to process element data: {e}")
                continue

        logger.info(f"Built unified element map with {len(unified_elements)} elements")
        return unified_elements

    def _collect_and_process_elements(self) -> List[Dict[str, Any]]:
        """
        Uses JavaScript to collect, filter, and extract ALL element data in one call.
        This eliminates ALL Python-Selenium communication overhead.
        """
        try:
            # JavaScript to do everything in the browser
            js_script = """
            // Get all elements using native DOM method (fastest)
            var allElements = document.getElementsByTagName("*");
            var processedElements = [];
            var refCounter = 0; // Initialize a counter for our refs
            
            // Define our target tags and attributes for filtering
            var staticTags = new Set(['div', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'th', 'td', 'tr', 'table', 'label', 'caption', 'span', 'strong', 'b', 'em', 'i', 'u', 'small', 'mark', 'dl', 'dt', 'dd']);
            var interactiveTags = new Set(['a', 'button', 'input', 'select', 'textarea']);
            
            // Helper function to check if element is visible (includes hidden interactive elements)
            function isElementVisible(elem) {
                var style = window.getComputedStyle(elem);
                
                // Check if element is a multiselect option or similar hidden interactive element
                var isHiddenInteractive = false;
                
                // Check for multiselect options (Vue.js multiselect pattern)
                if (elem.classList.contains('multiselect__option') || 
                    elem.classList.contains('multiselect__element') ||
                    elem.hasAttribute('data-select') ||
                    elem.hasAttribute('data-option') ||
                    elem.hasAttribute('data-value')) {
                    isHiddenInteractive = true;
                }
                
                // Check for dropdown options (common patterns)
                if (elem.classList.contains('dropdown-item') ||
                    elem.classList.contains('option') ||
                    elem.classList.contains('select-option') ||
                    elem.getAttribute('role') === 'option' ||
                    elem.getAttribute('role') === 'menuitem') {
                    isHiddenInteractive = true;
                }
                
                // Check if parent is a hidden dropdown/multiselect container
                var parent = elem.parentElement;
                var depth = 0;
                while (parent && parent !== document.body && depth < 3) { // Limit depth for performance
                    if (parent.classList.contains('multiselect__content') ||
                        parent.classList.contains('multiselect__content-wrapper') ||
                        parent.classList.contains('dropdown-menu') ||
                        parent.classList.contains('select-dropdown') ||
                        parent.getAttribute('role') === 'listbox' ||
                        parent.getAttribute('role') === 'menu') {
                        isHiddenInteractive = true;
                        break;
                    }
                    parent = parent.parentElement;
                    depth++;
                }
                
                // If it's a hidden interactive element, we still want to include it
                if (isHiddenInteractive) {
                    // For hidden interactive elements, just check they're not permanently hidden
                    return style.display !== 'none' || 
                           elem.offsetWidth > 0 || 
                           elem.offsetHeight > 0 ||
                           elem.textContent.trim().length > 0;
                }
                
                // Standard visibility check for regular elements
                return style.display !== 'none' && 
                       style.visibility !== 'hidden' && 
                       elem.offsetWidth > 0 && 
                       elem.offsetHeight > 0;
            }
            
            // Helper function to generate unique CSS selector
            function generateSelector(elem) {
                // Build a hierarchical selector for uniqueness
                // Note: We include IDs in the path but don't use them exclusively,
                // so the extraction agent can choose to use semantic elements instead of dynamic IDs
                var path = [];
                var current = elem;
                var maxDepth = 5; // Limit depth to prevent overly long selectors

                while (current && current.nodeType === Node.ELEMENT_NODE &&
                       current !== document.documentElement && path.length < maxDepth) {

                    var selector = current.tagName.toLowerCase();

                    // Add ID to this element's selector (but continue building path)
                    if (current.id) {
                        selector += '#' + current.id;
                    }

                    // Add meaningful classes (avoid utility classes)
                    if (current.className && typeof current.className === 'string') {
                        var classes = current.className.split(' ').filter(function(cls) {
                            if (!cls) return false;

                            // MUST filter: Classes with invalid CSS selector characters
                            // Square brackets: max-h-[1lh], w-[50%], top-[10px]
                            if (cls.includes('[') || cls.includes(']')) return false;

                            // Forward slashes: group/accessory (Tailwind group modifiers)
                            if (cls.includes('/')) return false;

                            // Colons: pseudo-classes
                            if (cls.includes(':')) return false;

                            // Filter out very common/generic utility class patterns
                            // These are everywhere and don't help with element uniqueness
                            if (cls.match(/^(v-theme--|v-btn--density|v-btn--size|v-btn--variant)/)) return false;
                            if (cls.match(/^(text-|bg-|border-|shadow-|opacity-)/)) return false;
                            if (cls.match(/^(p-\d|m-\d|pt-|pb-|pl-|pr-|px-|py-|mt-|mb-|ml-|mr-|mx-|my-)/)) return false;
                            if (cls.match(/^(w-\d|h-\d|min-|max-)/)) return false;
                            if (cls.match(/^(gap-\d|space-)/)) return false;

                            // Keep structural classes like flex, grid as they might be semantic
                            // but filter very short/generic ones
                            if (cls.length <= 2) return false;

                            return true;
                        });

                        if (classes.length > 0) {
                            // Use up to 3 most meaningful classes
                            var selectedClasses = classes.slice(0, 3);
                            selector += '.' + selectedClasses.join('.');
                        }
                    }
                    
                    // Add nth-child for disambiguation if needed
                    if (current.parentNode) {
                        var siblings = Array.from(current.parentNode.children);
                        var sameTagSiblings = siblings.filter(function(sibling) {
                            return sibling.tagName === current.tagName;
                        });
                        
                        if (sameTagSiblings.length > 1) {
                            var index = siblings.indexOf(current) + 1;
                            selector += ':nth-child(' + index + ')';
                        }
                    }
                    
                    path.unshift(selector);
                    current = current.parentNode;
                }

                return path.join(' > ');
            }
            
            // Helper function to check if element is interactive (enhanced)
            function isInteractive(elem, tagName) {
                // Standard interactive elements
                if (interactiveTags.has(tagName) ||
                    elem.hasAttribute('onclick') ||
                    elem.getAttribute('role') === 'button' ||
                    elem.getAttribute('role') === 'link' ||
                    elem.getAttribute('role') === 'checkbox' ||
                    elem.getAttribute('role') === 'tab' ||
                    elem.getAttribute('contenteditable') === 'true') {
                    return true;
                }
                
                // Custom interactive components detection
                
                // 1. Elements with tabindex="0" (focusable custom components)
                if (elem.getAttribute('tabindex') === '0') {
                    return true;
                }
                
                // 2. Elements with data attributes that suggest interactivity
                var dataAttrs = ['data-select', 'data-click', 'data-toggle', 'data-action', 
                               'data-selected', 'data-deselect', 'data-option', 'data-value'];
                for (var i = 0; i < dataAttrs.length; i++) {
                    if (elem.hasAttribute(dataAttrs[i])) {
                        return true;
                    }
                }
                
                // 3. CSS class patterns that indicate custom interactive components
                var className = elem.getAttribute('class') || '';
                var interactiveClassPatterns = [
                    'multiselect', 'dropdown', 'select', 'picker', 'chooser',
                    'toggle', 'switch', 'slider', 'accordion', 'tab',
                    'menu', 'popup', 'modal', 'dialog', 'overlay',
                    'clickable', 'selectable', 'interactive', 'control',
                    'widget', 'component'
                ];
                
                for (var i = 0; i < interactiveClassPatterns.length; i++) {
                    if (className.toLowerCase().includes(interactiveClassPatterns[i])) {
                        return true;
                    }
                }
                
                // 4. Elements with cursor pointer style (often indicates clickability)
                // BUT only for semantic elements, not generic containers/formatting tags
                // Generic containers with cursor:pointer are usually just wrappers around actual interactive elements
                var computedStyle = window.getComputedStyle(elem);
                if (computedStyle.cursor === 'pointer') {
                    // Skip generic containers and formatting tags - they're often just styled wrappers
                    // The actual interactive children inside them are more meaningful
                    var genericTags = ['div', 'span', 'strong', 'b', 'em', 'i', 'u', 'small', 'mark', 'p'];
                    if (genericTags.indexOf(tagName) !== -1) {
                        return false;
                    }

                    // For other elements with cursor:pointer, only consider them interactive if they have:
                    // - Text content, OR
                    // - Meaningful attributes (id, aria-label, title), OR
                    // - Meaningful class names (not just utility classes)
                    var hasText = elem.textContent && elem.textContent.trim().length > 0;
                    var hasId = elem.getAttribute('id') && elem.getAttribute('id').length > 0;
                    var hasAriaLabel = elem.getAttribute('aria-label') && elem.getAttribute('aria-label').length > 0;
                    var hasTitle = elem.getAttribute('title') && elem.getAttribute('title').length > 0;

                    var hasMeaningfulClass = false;
                    var classAttr = elem.getAttribute('class') || '';
                    if (classAttr) {
                        var classes = classAttr.split(/\s+/);
                        for (var j = 0; j < classes.length; j++) {
                            var cls = classes[j];
                            // Skip utility classes and consider only meaningful class names
                            if (cls.length > 3 &&
                                !cls.startsWith('css-') &&
                                !cls.startsWith('sc-') &&
                                !cls.startsWith('_') &&
                                !/^[a-zA-Z0-9]{5,8}$/.test(cls)) { // Skip random hash-like classes
                                hasMeaningfulClass = true;
                                break;
                            }
                        }
                    }

                    if (hasText || hasId || hasAriaLabel || hasTitle || hasMeaningfulClass) {
                        return true;
                    }
                }
                
                return false;
            }
            
            // Process elements with batching to prevent timeout
            // First pass: collect all interactive elements
            // Second pass: collect content elements up to limit
            var interactiveElements = [];
            var contentElements = [];
            var totalElements = allElements.length;

            // Pass 1: Collect ALL interactive elements (no limit)
            for (var i = 0; i < totalElements; i++) {
                var elem = allElements[i];
                var tagName = elem.tagName.toLowerCase();

                // Skip if not a target tag
                if (!staticTags.has(tagName) && !interactiveTags.has(tagName)) {
                    continue;
                }

                // Skip if not visible
                if (!isElementVisible(elem)) {
                    continue;
                }
                
                // Unified text collection strategy to prevent duplication
                var text = '';
                var childrenText = '';
                
                // Single function to get only direct text nodes (no recursion)
                function getDirectTextOnly(element) {
                    var result = '';
                    
                    // Skip script and style elements entirely
                    if (element.tagName === 'SCRIPT' || element.tagName === 'STYLE') {
                        return '';
                    }
                    
                    // Only collect direct text nodes, never recurse
                    for (var k = 0; k < element.childNodes.length; k++) {
                        var child = element.childNodes[k];
                        if (child.nodeType === Node.TEXT_NODE) {
                            result += child.textContent || '';
                        }
                    }
                    
                    return result.replace(/\s+/g, ' ').trim();
                }
                
                // Get the element's own direct text (never from children)
                text = getDirectTextOnly(elem);

                // Special handling for IMG elements - use alt text
                if (tagName === 'img' && !text) {
                    text = elem.getAttribute('alt') || '';
                }

                // Truncate if too long
                if (text && text.length > 300) {
                    text = text.substring(0, 300);
                }
                
                var isInteractiveElem = isInteractive(elem, tagName);

                // Only collect children_text for interactive elements that have no direct text
                // This prevents the "false parent" problem by being very selective
                if (isInteractiveElem && !text) {
                    // Collect text from immediate children only (not deep recursion)
                    var immediateChildrenText = '';
                    for (var j = 0; j < elem.children.length; j++) {
                        var child = elem.children[j];
                        if (child.tagName !== 'SCRIPT' && child.tagName !== 'STYLE') {
                            var childDirectText = getDirectTextOnly(child);
                            if (childDirectText) {
                                immediateChildrenText += childDirectText + ' ';
                            }
                        }
                    }

                    childrenText = immediateChildrenText.replace(/\s+/g, ' ').trim();
                    if (childrenText.length > 200) {
                        childrenText = childrenText.substring(0, 200);
                    }
                }

                // Check if element has meaningful attributes even without text
                var hasMeaningfulAttributes = (
                    elem.getAttribute('id') ||
                    elem.getAttribute('data-id') ||
                    elem.getAttribute('data-value') ||
                    tagName === 'tr' ||  // Always include TR elements for table context
                    tagName === 'img'    // Always include IMG elements (they have src/alt attributes)
                );

                // Skip elements with no meaningful content unless interactive or has meaningful attributes
                if (!text && !childrenText && !isInteractiveElem && !hasMeaningfulAttributes) {
                    continue;
                }

                // Separate interactive elements from content elements
                var targetList = isInteractiveElem ? interactiveElements : contentElements;

                // Limit content elements to 500, but NO LIMIT on interactive elements
                if (!isInteractiveElem && contentElements.length >= 500) {
                    continue;
                }

                // Set the data-agent-ref attribute on the actual DOM element
                var currentRef = interactiveElements.length + contentElements.length;
                elem.setAttribute('data-agent-ref', currentRef);

                // Collect all data-* attributes (except data-agent-ref which is temporary)
                var dataAttributes = {};
                for (var k = 0; k < elem.attributes.length; k++) {
                    var attr = elem.attributes[k];
                    if (attr.name.startsWith('data-') && attr.name !== 'data-agent-ref') {
                        dataAttributes[attr.name] = attr.value;
                    }
                }

                // For TR elements, collect TD/TH children data for context
                var tableCells = [];
                if (tagName === 'tr') {
                    var cells = elem.querySelectorAll('td, th');
                    for (var c = 0; c < cells.length; c++) {
                        var cell = cells[c];
                        tableCells.push({
                            text: cell.textContent.trim(),
                            data_label: cell.getAttribute('data-label') || '',
                            title: cell.getAttribute('title') || ''
                        });
                    }
                }

                // Build the element data object (simplified)
                var elementData = {
                    ref: currentRef, // Use the calculated ref
                    tag: tagName,
                    text: text,
                    children_text: childrenText,
                    is_interactive: isInteractiveElem,
                    css_selector: generateSelector(elem),
                    attributes: {
                        id: elem.getAttribute('id') || '',
                        'aria-label': elem.getAttribute('aria-label') || '',
                        placeholder: elem.getAttribute('placeholder') || '',
                        'class': elem.getAttribute('class') || '',
                        value: elem.getAttribute('value') || '',
                        name: elem.getAttribute('name') || '',
                        type: elem.getAttribute('type') || '',
                        href: elem.getAttribute('href') || '',
                        title: elem.getAttribute('title') || '',
                        alt: elem.getAttribute('alt') || '',
                        src: elem.getAttribute('src') || '',
                        disabled: elem.disabled || elem.hasAttribute('disabled') || false
                    },
                    data_attributes: dataAttributes,
                    table_cells: tableCells
                };

                // Push to the appropriate list
                targetList.push(elementData);
            }

            // Combine interactive and content elements
            // Interactive elements first (they're more important for agent actions)
            return interactiveElements.concat(contentElements);
            """
            
            # Execute JavaScript and get fully processed element data
            element_data = self.driver.execute_script(js_script)
            logger.debug(f"Processed {len(element_data)} elements using JavaScript")
            return element_data
            
        except Exception as e:
            logger.error(f"Failed to collect and process elements: {e}")
            return []

    def _generate_css_selector(self, element: WebElement) -> str:
        """
        Generate a simple CSS selector for an element.
        """
        try:
            # Try to use ID first if available
            element_id = element.get_attribute('id')
            if element_id:
                return f"#{element_id}"
            
            # Get tag name
            tag = element.tag_name.lower()
            
            # Try to use class if available
            class_name = element.get_attribute('class')
            if class_name:
                # Use first class that's not too generic
                classes = class_name.strip().split()
                for cls in classes:
                    if cls and len(cls) > 2 and not cls.startswith(('w-', 'h-', 'p-', 'm-', 'text-', 'bg-')):
                        return f"{tag}.{cls}"
            
            # Fallback to just tag name
            return tag
            
        except Exception as e:
            logger.warning(f"Failed to generate CSS selector: {e}")
            return element.tag_name.lower()

    def _truncate_text(self, text: str, max_length: int = 150) -> str:
        """
        Truncate text to a maximum length with ellipsis if needed.
        Preserves readability while keeping content manageable for LLM processing.
        """
        if not text or len(text) <= max_length:
            return text
        return text[:max_length].rstrip() + "..."
    
    def _truncate_url(self, url: str, max_length: int = 100) -> str:
        """
        Truncate URLs intelligently, preserving the domain and important parts.
        For very long URLs, shows beginning and end with ellipsis in middle.
        """
        if not url or len(url) <= max_length:
            return url
        
        # For URLs, try to preserve the domain and end
        if url.startswith(('http://', 'https://')):
            # Find the domain part
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                domain = f"{parsed.scheme}://{parsed.netloc}"
                
                if len(domain) >= max_length - 10:
                    # Domain itself is too long, just truncate normally
                    return url[:max_length].rstrip() + "..."
                
                remaining_length = max_length - len(domain) - 6  # 6 for ".../"
                if remaining_length > 0:
                    path_part = parsed.path + (f"?{parsed.query}" if parsed.query else "")
                    if len(path_part) <= remaining_length:
                        return url
                    else:
                        # Show domain + ... + end of path
                        end_part = path_part[-remaining_length//2:] if remaining_length > 10 else ""
                        return f"{domain}/...{end_part}"
            except:
                # Fallback to simple truncation if URL parsing fails
                pass
        
        # Simple truncation for non-URLs or if parsing failed
        return url[:max_length].rstrip() + "..."

    def _format_content_map_for_prompt(self, content_elements: ElementInfoList, map_type: str = "lean") -> str:
        """
        Converts the content element map into a format for LLM analysis.

        Args:
            content_elements: List of content elements to format
            map_type: "rich" includes CSS selectors, "lean" uses ref system
        """
        # Apply compression to reduce repetitive patterns
        compressed_items = self._compress_repetitive_patterns(content_elements)

        # Log compression statistics
        total_elements = len(content_elements)
        compressed_groups = [item for item in compressed_items if item["type"] == "compressed"]
        if compressed_groups:
            total_hidden = sum(item["count"] - len(item["shown"]) for item in compressed_groups)
            logger.info(f"Content map: Compressed {len(compressed_groups)} repetitive patterns, hiding {total_hidden} elements from {total_elements} total")

        prompt_lines: List[str] = []

        for item in compressed_items:
            if item["type"] == "element":
                # Format a single element normally
                element_data = item["element"]
                formatted_line = self._format_single_content_element(element_data, map_type)
                if formatted_line:  # Only add if not skipped
                    prompt_lines.append(formatted_line)

            elif item["type"] == "compressed":
                # Format a compressed group
                pattern = item["pattern"]
                count = item["count"]
                shown = item["shown"]
                show_first = item["show_first"]
                show_last = item["show_last"]

                # Add the shown elements
                for i, elem in enumerate(shown[:show_first]):
                    formatted_line = self._format_single_content_element(elem, map_type)
                    if formatted_line:
                        prompt_lines.append(formatted_line)

                # Add compression notice
                hidden_count = count - len(shown)
                if hidden_count > 0:
                    if map_type == "rich":
                        prompt_lines.append(f"... [{hidden_count} more elements with pattern: {pattern}]")
                    else:
                        prompt_lines.append(f"... [{hidden_count} more similar elements]")

                # Add last elements if any
                if len(shown) > show_first:
                    for elem in shown[show_first:]:
                        formatted_line = self._format_single_content_element(elem, map_type)
                        if formatted_line:
                            prompt_lines.append(formatted_line)

        return "\n".join(prompt_lines)

    def _format_single_content_element(self, element_data: PageElement, map_type: str) -> Optional[str]:
        """
        Formats a single content element.
        Returns None if the element should be skipped.
        """
        text = element_data.text.strip()
        css_selector = element_data.css_selector
        element_id = element_data.attributes.id
        title = element_data.attributes.title

        # Skip elements with no meaningful text content AND no meaningful attributes
        has_meaningful_attrs = element_id or title or element_data.data_attributes
        if not text and not has_meaningful_attrs:
            return None

        # Build attribute parts
        attr_parts = []

        # Add ID if present
        if element_id:
            attr_parts.append(f'id="{element_id}"')

        # Add title if present
        if title:
            truncated_title = self._truncate_text(title, 100)
            attr_parts.append(f'title="{truncated_title}"')

        # Add important data-* attributes (exclude data-agent-ref as it's temporary)
        if element_data.data_attributes:
            for data_key, data_value in element_data.data_attributes.items():
                if data_key != 'data-agent-ref':  # Skip temporary ref attribute
                    truncated_value = self._truncate_text(data_value, 100)
                    attr_parts.append(f'{data_key}="{truncated_value}"')

        # Truncate text for better readability
        truncated_text = self._truncate_text(text, 200) if text else ""

        # Format based on map_type: rich includes CSS selector, lean uses ref
        if map_type == "rich":
            base = f'CSS: {css_selector} | TAG: {element_data.tag}'
        else:  # lean
            base = f'ref="{element_data.ref}" | TAG: {element_data.tag}'

        # Add attributes if any
        if attr_parts:
            base += " | " + " ".join(attr_parts)

        # Special formatting for TR elements with table cells
        if element_data.tag == 'tr' and element_data.table_cells:
            cell_parts = []
            for cell in element_data.table_cells:
                cell_text = self._truncate_text(cell['text'], 50) if cell['text'] else ""
                label = cell.get('data_label', '')

                if label and cell_text:
                    cell_parts.append(f"{label}={cell_text}")
                elif cell_text:
                    cell_parts.append(cell_text)

            if cell_parts:
                base += f' | ROW: {" | ".join(cell_parts)}'

        # Add text if present (and not a TR element with cells already shown)
        elif truncated_text:
            base += f' | Text: {truncated_text}'

        return base













    def _deduplicate_nested_elements(self, interactive_elements: ElementInfoList) -> ElementInfoList:
        """
        Enhanced deduplication that handles nested elements and identical text cases.
        
        This method addresses several deduplication challenges:
        1. Nested elements where child text is contained within parent text
        2. "False parents" created by children_text collection
        3. Multiple elements with identical text but unclear hierarchy
        
        The strategy is to:
        - Group elements by identical text content
        - Within each group, identify true parent-child relationships using DOM hierarchy
        - Remove redundant children while preserving the most meaningful parent
        - Handle edge cases where hierarchy is ambiguous
        """
        if not interactive_elements:
            return interactive_elements

        refs_to_remove = set()
        
        # Group elements by their effective text content (text or children_text)
        text_groups = {}
        for elem in interactive_elements:
            effective_text = elem.text.strip() if elem.text.strip() else elem.children_text.strip()
            if effective_text:  # Only process elements with text
                if effective_text not in text_groups:
                    text_groups[effective_text] = []
                text_groups[effective_text].append(elem)
        
        # Process each group of elements with identical text
        for text_content, elements in text_groups.items():
            if len(elements) <= 1:
                continue  # No duplicates to handle
                
            logger.debug(f"Processing {len(elements)} elements with identical text: '{text_content[:50]}...'")
            
            # Sort elements by CSS selector length (shorter = higher in DOM hierarchy)
            elements_by_hierarchy = sorted(elements, key=lambda x: len(x.css_selector))
            
            # Find true parent-child relationships within this group
            for i, potential_parent in enumerate(elements_by_hierarchy):
                if potential_parent.ref in refs_to_remove:
                    continue
                    
                parent_selector = potential_parent.css_selector
                
                # Look for children nested within this parent
                for j, potential_child in enumerate(elements_by_hierarchy[i+1:], i+1):
                    if potential_child.ref in refs_to_remove:
                        continue
                    
                    child_selector = potential_child.css_selector
                    
                    # Check if child is actually nested within parent using CSS selector analysis
                    is_nested = (
                        child_selector.startswith(parent_selector + " ") or
                        child_selector.startswith(parent_selector + ">") or
                        (parent_selector in child_selector and len(child_selector) > len(parent_selector))
                    )
                    
                    if is_nested:
                        # ALWAYS prioritize actual interactive elements over containers
                        parent_is_interactive = potential_parent.tag.lower() in ['a', 'button', 'input', 'select', 'textarea']
                        child_is_interactive = potential_child.tag.lower() in ['a', 'button', 'input', 'select', 'textarea']
                        
                        if child_is_interactive and not parent_is_interactive:
                            # Child is interactive, parent is container -> keep child
                            refs_to_remove.add(potential_parent.ref)
                            logger.debug(f"Removing container parent {potential_parent.ref} in favor of interactive child {potential_child.ref}")
                            break  # Parent is removed, no need to check more children
                        elif parent_is_interactive and not child_is_interactive:
                            # Parent is interactive, child is not -> keep parent
                            refs_to_remove.add(potential_child.ref)
                            logger.debug(f"Removing non-interactive child {potential_child.ref} in favor of interactive parent {potential_parent.ref}")
                        else:
                            # Both interactive or both non-interactive -> use quality score
                            parent_quality = self._calculate_element_quality(potential_parent)
                            child_quality = self._calculate_element_quality(potential_child)
                            
                            if parent_quality >= child_quality:
                                refs_to_remove.add(potential_child.ref)
                                logger.debug(f"Removing nested child element {potential_child.ref} in favor of parent {potential_parent.ref}")
                            else:
                                refs_to_remove.add(potential_parent.ref)
                                logger.debug(f"Removing parent element {potential_parent.ref} in favor of higher-quality child {potential_child.ref}")
                                break  # Parent is removed, no need to check more children
            
            # Handle remaining duplicates in this group (elements with identical text but no clear hierarchy)
            remaining_elements = [elem for elem in elements if elem.ref not in refs_to_remove]
            if len(remaining_elements) > 1:
                # Keep the highest quality element and remove the rest
                best_element = max(remaining_elements, key=self._calculate_element_quality)
                for elem in remaining_elements:
                    if elem.ref != best_element.ref:
                        refs_to_remove.add(elem.ref)
                        logger.debug(f"Removing duplicate element {elem.ref} in favor of higher-quality element {best_element.ref}")

        # Also handle traditional nested element cases (child text subset of parent text)
        sorted_elements = sorted(interactive_elements, key=lambda x: len(x.css_selector))
        
        for i, parent in enumerate(sorted_elements):
            if parent.ref in refs_to_remove:
                continue

            parent_text = parent.text.strip() if parent.text.strip() else parent.children_text.strip()
            if not parent_text:
                continue

            # Look for children that are nested inside this parent
            for j, child in enumerate(sorted_elements):
                if i == j or child.ref in refs_to_remove:
                    continue

                # Check for nesting: the child's selector should start with the parent's selector
                is_nested = (
                    child.css_selector.startswith(parent.css_selector + " ") or
                    child.css_selector.startswith(parent.css_selector + ">") or
                    (parent.css_selector in child.css_selector and len(child.css_selector) > len(parent.css_selector))
                )
                
                if is_nested:
                    child_text = child.text.strip() if child.text else child.children_text.strip()
                    
                    # Special case: Don't remove individual pagination/navigation links
                    # These often have single digit/word text that appears in parent's children_text
                    is_likely_pagination = (
                        child.tag.lower() == 'a' and 
                        child_text and 
                        len(child_text) <= 3 and  # Short text like "1", "2", "Next"
                        (child_text.isdigit() or child_text.lower() in ['next', 'prev', 'previous', '...'])
                    )
                    
                    # If the child's text is a subset of the parent's text, mark it for removal
                    # UNLESS it's likely a pagination link or other important interactive element
                    if (child_text and child_text in parent_text and child_text != parent_text and 
                        not is_likely_pagination):
                        refs_to_remove.add(child.ref)
                        logger.debug(f"Removing nested element {child.ref} with subset text '{child_text[:30]}...' of parent {parent.ref}")

        # Filter the original list to keep only the elements not marked for removal
        deduplicated_elements = [elem for elem in interactive_elements if elem.ref not in refs_to_remove]
        
        logger.info(f"Enhanced deduplication removed {len(refs_to_remove)} elements: {len(interactive_elements)} -> {len(deduplicated_elements)}")
        return deduplicated_elements
    
    def _calculate_element_quality(self, element: PageElement) -> int:
        """
        Calculate a quality score for an element to determine which one to keep in deduplication.
        Higher score = better quality element.
        
        Factors considered:
        1. Has direct text vs children_text (direct text is better)
        2. Tag semantic value (a, button > div, span)
        3. Number of meaningful attributes
        4. CSS selector specificity (shorter is often better, but not always)
        """
        score = 0
        
        # Prefer elements with direct text over children_text
        if element.text.strip():
            score += 100
        elif element.children_text.strip():
            score += 50
        
        # Tag priority (semantic elements are better)
        tag_scores = {
            'a': 50, 'button': 45, 'input': 40, 'select': 35, 'textarea': 30,
            'label': 25, 'span': 15, 'div': 10, 'p': 20
        }
        score += tag_scores.get(element.tag.lower(), 5)
        
        # Attribute richness (more meaningful attributes = better)
        if element.attributes.id:
            score += 20
        if element.attributes.href:
            score += 15
        if element.attributes.aria_label:
            score += 10
        if element.attributes.type:
            score += 8
        if element.attributes.name:
            score += 5
        if element.attributes.value:
            score += 5
        
        # CSS selector length penalty (very long selectors might indicate deep nesting)
        # But don't penalize too heavily as sometimes specific selectors are necessary
        if len(element.css_selector) > 100:
            score -= 5
        elif len(element.css_selector) > 200:
            score -= 10
        
        return score
    
    def _select_best_element_from_group(self, elements: List[PageElement]) -> PageElement:
        """
        Select the best element from a group of elements with similar text content.
        Priority:
        1. Elements with direct text over children_text
        2. More semantic tags (a, button, input) over generic ones (div, span)
        3. Elements with more attributes (id, href, etc.)
        4. Shorter CSS selectors (usually more direct)
        """
        # Tag priority (higher number = better)
        tag_priority = {
            'a': 10, 'button': 9, 'input': 8, 'select': 7, 'textarea': 6,
            'span': 3, 'div': 1, 'p': 2
        }
        
        def element_score(element: PageElement) -> tuple:
            # Score components (all should be comparable)
            has_direct_text = 1 if element.text.strip() else 0
            tag_score = tag_priority.get(element.tag.lower(), 0)
            
            # Count meaningful attributes
            attr_count = sum([
                1 if element.attributes.id else 0,
                1 if element.attributes.href else 0,
                1 if element.attributes.aria_label else 0,
                1 if element.attributes.type else 0,
                1 if element.attributes.name else 0,
                1 if element.attributes.value else 0,
            ])
            
            # Prefer shorter CSS selectors (more direct elements)
            css_length_penalty = len(element.css_selector) // 10  # Divide by 10 to keep it small
            
            return (has_direct_text, tag_score, attr_count, -css_length_penalty)
        
        # Sort by score (descending) and return the best
        elements.sort(key=element_score, reverse=True)
        return elements[0]

    def _extract_css_pattern(self, css_selector: str) -> str:
        """
        Extracts a pattern from a CSS selector by replacing variable parts with wildcards.

        Examples:
            "#g_1_W4vHttEb > a.eventRowLink" -> "#g_1_* > a.eventRowLink"
            "div:nth-child(5)" -> "div:nth-child(*)"
            "#user-123 > span" -> "#user-* > span"
        """
        import re

        # Replace IDs with random-looking suffixes (letters/numbers after underscore or dash)
        pattern = re.sub(r'#([\w-]+?)_[A-Za-z0-9]{6,}', r'#\1_*', css_selector)
        pattern = re.sub(r'#([\w-]+?)-[A-Za-z0-9]{6,}', r'#\1-*', pattern)

        # Replace standalone IDs that look like random hashes
        pattern = re.sub(r'#[A-Za-z0-9]{8,}(?=\s|>|$)', '#*', pattern)

        # Replace nth-child numbers
        pattern = re.sub(r':nth-child\(\d+\)', ':nth-child(*)', pattern)

        # Replace standalone numbers in IDs (like #user-123)
        pattern = re.sub(r'([_-])\d+(?=\s|>|\.|\[|$)', r'\1*', pattern)

        return pattern

    def _group_elements_by_pattern(self, elements: ElementInfoList) -> Dict[str, List[PageElement]]:
        """
        Groups elements by their CSS selector pattern.
        Returns a dict mapping pattern -> list of elements with that pattern.
        """
        pattern_groups = {}

        for elem in elements:
            pattern = self._extract_css_pattern(elem.css_selector)
            if pattern not in pattern_groups:
                pattern_groups[pattern] = []
            pattern_groups[pattern].append(elem)

        return pattern_groups

    def _compress_repetitive_patterns(self, deduplicated_elements: ElementInfoList,
                                     compression_threshold: int = 15,
                                     show_first: int = 10,
                                     show_last: int = 2) -> List[Dict[str, Any]]:
        """
        Detects repetitive patterns in elements and compresses them while preserving order.

        This detects both:
        1. Consecutive runs of identical patterns (e.g., 50 identical divs in a row)
        2. Repeating multi-element sequences (e.g., 100 match rows, each with div+div+span+span+span+span)

        Returns a list of items, where each item is either:
        - {"type": "element", "element": PageElement} - a single element to show
        - {"type": "compressed", "pattern": str, "count": int, "shown": List[PageElement]} - a compressed group
        """
        if not deduplicated_elements:
            return []

        # First, try to detect repeating multi-element sequences
        sequence_result = self._detect_repeating_sequences(deduplicated_elements, compression_threshold, show_first, show_last)
        if sequence_result:
            return sequence_result

        # Fallback: Compress consecutive runs of identical patterns
        result = []
        i = 0

        while i < len(deduplicated_elements):
            current_elem = deduplicated_elements[i]
            current_pattern = self._extract_css_pattern(current_elem.css_selector)

            # Look ahead to find consecutive elements with the same pattern
            run_length = 1
            j = i + 1
            while j < len(deduplicated_elements):
                next_pattern = self._extract_css_pattern(deduplicated_elements[j].css_selector)
                if next_pattern == current_pattern:
                    run_length += 1
                    j += 1
                else:
                    break

            # If we found a long run of the same pattern, compress it
            if run_length >= compression_threshold:
                run_elements = deduplicated_elements[i:i+run_length]

                # Show first N and last M elements from this run
                shown_elements = (run_elements[:show_first] + run_elements[-show_last:]
                                if run_length > show_first + show_last
                                else run_elements)

                result.append({
                    "type": "compressed",
                    "pattern": current_pattern,
                    "count": run_length,
                    "shown": shown_elements,
                    "show_first": show_first,
                    "show_last": show_last
                })

                i += run_length
            else:
                # Not a long enough run, show elements normally
                for k in range(run_length):
                    result.append({
                        "type": "element",
                        "element": deduplicated_elements[i + k]
                    })
                i += run_length

        return result

    def _detect_repeating_sequences(self, elements: ElementInfoList,
                                   compression_threshold: int,
                                   show_first: int,
                                   show_last: int) -> Optional[List[Dict[str, Any]]]:
        """
        Detects repeating multi-element sequences (e.g., match rows with div+div+span+span+span+span).

        Tries different sequence lengths (2-10 elements) and looks for the length that has
        the most repetitions. If we find a repeating sequence, compress all instances.
        """
        if len(elements) < compression_threshold:
            return None

        # Create signatures for each element (tag + data attributes only)
        # Don't use CSS patterns here as they vary per element even when semantically identical
        signatures = []
        for elem in elements:
            # Include key data attributes in signature to distinguish different types
            data_attrs = sorted([k for k in elem.data_attributes.keys() if k != 'data-agent-ref'])
            # Use only tag and data attributes - this is more robust for detecting semantic patterns
            signature = f"{elem.tag}:{','.join(data_attrs)}"
            signatures.append(signature)

        # Try different sequence lengths (2 to 10 elements)
        best_sequence_length = None
        best_repetition_count = 0

        for seq_length in range(2, min(11, len(elements) // 3)):  # At least 3 repetitions needed
            # Check if this sequence length divides the element list reasonably
            # We'll look for the most common sequence of this length
            sequence_counts = {}

            for i in range(0, len(signatures) - seq_length + 1, seq_length):
                # Get this sequence
                seq = tuple(signatures[i:i+seq_length])
                sequence_counts[seq] = sequence_counts.get(seq, 0) + 1

            # Find the most common sequence of this length
            if sequence_counts:
                max_count = max(sequence_counts.values())
                if max_count >= compression_threshold // seq_length:  # Adjust threshold for sequence length
                    if max_count > best_repetition_count:
                        best_repetition_count = max_count
                        best_sequence_length = seq_length

        # If we found a good repeating sequence, compress it
        if best_sequence_length and best_repetition_count >= 3:
            logger.info(f"Detected repeating sequence of length {best_sequence_length}, repeated {best_repetition_count} times")

            result = []
            i = 0
            sequence_instances = 0

            # Process elements in chunks of the sequence length
            while i < len(elements):
                # Check if we're at the start of a repeating sequence
                current_sig = tuple(signatures[i:i+best_sequence_length])

                # Count how many consecutive instances of this sequence we have
                instances = 0
                j = i
                while j + best_sequence_length <= len(elements):
                    if tuple(signatures[j:j+best_sequence_length]) == current_sig:
                        instances += 1
                        j += best_sequence_length
                    else:
                        break

                # If we found multiple instances, compress them
                if instances >= 3:  # At least 3 repetitions to compress
                    total_elements = instances * best_sequence_length
                    all_sequence_elements = elements[i:i+total_elements]

                    # Show first N and last M sequences (not individual elements)
                    sequences_to_show = show_first + show_last
                    if instances > sequences_to_show:
                        shown_sequences_indices = (
                            list(range(show_first)) +  # First N sequences
                            list(range(instances - show_last, instances))  # Last M sequences
                        )
                        shown_elements = []
                        for seq_idx in shown_sequences_indices:
                            start = seq_idx * best_sequence_length
                            shown_elements.extend(all_sequence_elements[start:start+best_sequence_length])
                    else:
                        shown_elements = all_sequence_elements

                    result.append({
                        "type": "compressed",
                        "pattern": f"repeating sequence of {best_sequence_length} elements",
                        "count": total_elements,
                        "shown": shown_elements,
                        "show_first": show_first * best_sequence_length,
                        "show_last": show_last * best_sequence_length
                    })

                    i += total_elements
                    sequence_instances += instances
                else:
                    # Not enough repetitions, show normally
                    for k in range(min(best_sequence_length if instances > 0 else 1, len(elements) - i)):
                        result.append({
                            "type": "element",
                            "element": elements[i + k]
                        })
                    i += min(best_sequence_length if instances > 0 else 1, len(elements) - i)

            if sequence_instances > 0:
                return result

        return None

    def _format_interactive_map_for_prompt(self, interactive_elements: ElementInfoList, map_type: str = "lean") -> str:
        """
        Converts the interactive element map into a simplified, single string for the LLM.

        Args:
            interactive_elements: List of interactive elements to format
            map_type: "rich" includes CSS selectors, "lean" uses ref system
        """
        # First, deduplicate nested elements
        deduplicated_elements = self._deduplicate_nested_elements(interactive_elements)

        # Then compress repetitive patterns
        compressed_items = self._compress_repetitive_patterns(deduplicated_elements)

        # Log compression statistics
        total_elements = len(deduplicated_elements)
        compressed_groups = [item for item in compressed_items if item["type"] == "compressed"]
        if compressed_groups:
            total_hidden = sum(item["count"] - len(item["shown"]) for item in compressed_groups)
            logger.info(f"Compressed {len(compressed_groups)} repetitive patterns, hiding {total_hidden} elements from {total_elements} total")

        prompt_lines: List[str] = []

        for item in compressed_items:
            if item["type"] == "element":
                # Format a single element normally
                element_data = item["element"]
                formatted_line = self._format_single_element(element_data, map_type)
                if formatted_line:  # Only add if not skipped
                    prompt_lines.append(formatted_line)

            elif item["type"] == "compressed":
                # Format a compressed group
                pattern = item["pattern"]
                count = item["count"]
                shown = item["shown"]
                show_first = item["show_first"]
                show_last = item["show_last"]

                # Add the shown elements
                for i, elem in enumerate(shown[:show_first]):
                    formatted_line = self._format_single_element(elem, map_type)
                    if formatted_line:
                        prompt_lines.append(formatted_line)

                # Add compression notice
                hidden_count = count - len(shown)
                if hidden_count > 0:
                    if map_type == "rich":
                        prompt_lines.append(f"... [{hidden_count} more elements with pattern: {pattern}]")
                    else:
                        prompt_lines.append(f"... [{hidden_count} more similar elements]")

                # Add last elements if any
                if len(shown) > show_first:
                    for elem in shown[show_first:]:
                        formatted_line = self._format_single_element(elem, map_type)
                        if formatted_line:
                            prompt_lines.append(formatted_line)

        return "\n".join(prompt_lines)

    def _format_single_element(self, element_data: PageElement, map_type: str) -> Optional[str]:
        """
        Formats a single element for the interactive map.
        Returns None if the element should be skipped.
        """
        text = element_data.text.strip()
        tag = element_data.tag
        css_selector = element_data.css_selector

        # Build a description for this interactive element
        description_parts = []

        # Add tag information
        description_parts.append(f"{tag} ")

        # Add text if available
        if text:
            truncated_text = self._truncate_text(text, 100)
            description_parts.append(f'TEXT:"{truncated_text}"')
        elif element_data.children_text:
            # If no direct text but has children text, show that instead
            truncated_children_text = self._truncate_text(element_data.children_text, 100)
            description_parts.append(f'CHILDREN_TEXT:"{truncated_children_text}"')

        # Add aria-label if available
        if element_data.attributes.aria_label:
            truncated_aria_label = self._truncate_text(element_data.attributes.aria_label, 50)
            description_parts.append(f'aria-label="{truncated_aria_label}"')

        # Add placeholder if available
        if element_data.attributes.placeholder:
            truncated_placeholder = self._truncate_text(element_data.attributes.placeholder, 50)
            description_parts.append(f'placeholder="{truncated_placeholder}"')

        # Add ID if available
        if element_data.attributes.id:
            description_parts.append(f'id="{element_data.attributes.id}"')

        # Add value if available (for form inputs)
        if element_data.attributes.value:
            truncated_value = self._truncate_text(element_data.attributes.value, 50)
            description_parts.append(f'value="{truncated_value}"')

        # Add name if available (for form inputs)
        if element_data.attributes.name:
            description_parts.append(f'name="{element_data.attributes.name}"')

        # Add type if available (for form inputs)
        if element_data.attributes.type:
            description_parts.append(f'type="{element_data.attributes.type}"')

        # Add href if available (for links)
        if element_data.attributes.href:
            truncated_href = self._truncate_url(element_data.attributes.href, 80)
            description_parts.append(f'href="{truncated_href}"')

        # Add title if available
        if element_data.attributes.title:
            truncated_title = self._truncate_text(element_data.attributes.title, 50)
            description_parts.append(f'title="{truncated_title}"')

        # Add disabled state if element is disabled
        if element_data.attributes.disabled:
            description_parts.append(f'disabled="{element_data.attributes.disabled}"')

        # Check if element has any meaningful identifiers
        has_identifiers = any([
            text,
            element_data.children_text,
            element_data.attributes.aria_label,
            element_data.attributes.placeholder,
            element_data.attributes.id,
            element_data.attributes.value,
            element_data.attributes.name,
            element_data.attributes.type,
            element_data.attributes.href,
            element_data.attributes.title
        ])

        # Skip elements with no meaningful identifiers (empty divs, spans, etc.)
        if not has_identifiers:
            return None

        description = " ".join(description_parts)

        # Format based on map_type: rich includes CSS selector, lean uses ref
        if map_type == "rich":
            return f'CSS: {css_selector} | TYPE: {description}'
        else:  # lean
            return f'ref="{element_data.ref}" | TYPE: {description}'

    def _is_element_interactive(self, element: WebElement, tag_name: str) -> bool:
        """
        Checks if a given WebElement is interactive.
        """
        try:
            # Check for disabled or readonly states
            if not element.is_enabled():
                return False
            if tag_name in ['input', 'textarea'] and element.get_attribute('readonly'):
                return False

            # Check if tag is inherently interactive
            if tag_name in self.INTERACTIVE_TAGS:
                return True
            
            # Check for interactive attributes
            if element.get_attribute('onclick') or element.get_attribute('contenteditable') == 'true':
                return True
            
            # Check for interactive roles
            role = element.get_attribute('role')
            if role in ['button', 'link', 'menuitem', 'tab', 'checkbox', 'radio']:
                return True

            return False
            
        except StaleElementReferenceException:
            logger.warning("Element became stale during interactivity check.")
            return False

    def _cleanup_interactive_markers(self):
        """
        Removes all temporary data-agent-ref attributes from the page.
        This is called when we're done with element interactions or when parsing a new page.
        """
        try:
            self.driver.execute_script("""
                var elements = document.querySelectorAll('[data-agent-ref]');
                for (var i = 0; i < elements.length; i++) {
                    elements[i].removeAttribute('data-agent-ref');
                }
            """)
            logger.debug("Cleaned up interactive markers from page")
        except Exception as e:
            logger.warning(f"Failed to clean up interactive markers: {e}")

    def _cleanup_content_markers(self):
        """
        Removes the temporary 'data-agent-ref' attributes from the DOM.
        Should be called before each new element map generation.
        """
        logger.debug("Cleaning up old element markers from page...")
        try:
            self.driver.execute_script(
                "document.querySelectorAll('[data-agent-ref]').forEach(el => el.removeAttribute('data-agent-ref'));"
            )
        except Exception as e:
            logger.warning(f"Could not clean up element markers: {e}")


def generate_page_map(driver: Driver, max_text_length: int = 500) -> List[PageElement]:
    """
    Generate a map of all elements on the page using SeleniumBase Driver
    
    Args:
        driver: SeleniumBase Driver instance
        max_text_length: Maximum length for text content
        
    Returns:
        List of PageElement objects representing page elements
    """
    parser = PageParser(driver)
    interactive_elements, _ = parser.get_interactive_map()
    content_elements, _ = parser.get_content_map()
    
    # Combine and sort by index
    all_elements = interactive_elements + content_elements
    all_elements.sort(key=lambda x: x.index)
    
    return all_elements


def find_element_by_text(driver: Driver, text: str, tag: str = "*") -> Optional[WebElement]:
    """
    Find an element by its text content using SeleniumBase
    
    Args:
        driver: SeleniumBase Driver instance
        text: Text to search for
        tag: HTML tag to limit search to (default: any tag)
        
    Returns:
        WebElement if found, None otherwise
    """
    try:
        xpath = f"//{tag}[contains(text(), '{text}')]"
        return driver.find_element("xpath", xpath)
    except Exception:
        return None


def find_elements_by_text(driver: Driver, text: str, tag: str = "*") -> List[WebElement]:
    """
    Find all elements by their text content using SeleniumBase
    
    Args:
        driver: SeleniumBase Driver instance
        text: Text to search for
        tag: HTML tag to limit search to (default: any tag)
        
    Returns:
        List of WebElements
    """
    try:
        xpath = f"//{tag}[contains(text(), '{text}')]"
        return driver.find_elements("xpath", xpath)
    except Exception:
        return []


def get_element_info(element: WebElement) -> Dict[str, Any]:
    """
    Get comprehensive information about a WebElement
    
    Args:
        element: WebElement
        
    Returns:
        Dictionary with element information
    """
    try:
        return {
            'tag_name': element.tag_name,
            'text': element.text,
            'id': element.get_attribute('id'),
            'class': element.get_attribute('class'),
            'name': element.get_attribute('name'),
            'value': element.get_attribute('value'),
            'href': element.get_attribute('href'),
            'src': element.get_attribute('src'),
            'alt': element.get_attribute('alt'),
            'title': element.get_attribute('title'),
            'placeholder': element.get_attribute('placeholder'),
            'type': element.get_attribute('type'),
            'disabled': element.get_attribute('disabled'),
            'is_displayed': element.is_displayed(),
            'is_enabled': element.is_enabled(),
            'is_selected': element.is_selected() if element.tag_name in ['input', 'option'] else None,
            'location': element.location,
            'size': element.size
        }
    except Exception as e:
        logger.warning(f'Error getting element info: {e}')
        return {}


def wait_for_element_visible(driver: Driver, selector: str, timeout: int = 10) -> Optional[WebElement]:
    """
    Wait for an element to become visible using SeleniumBase
    
    Args:
        driver: SeleniumBase Driver instance
        selector: CSS selector or XPath
        timeout: Maximum time to wait in seconds
        
    Returns:
        WebElement if found and visible, None otherwise
    """
    try:
        # Use SeleniumBase's built-in wait methods
        if selector.startswith('/') or selector.startswith('('):
            # XPath
            driver.wait_for_element(selector, by="xpath", timeout=timeout)
            return driver.find_element("xpath", selector)
        else:
            # CSS selector
            driver.wait_for_element(selector, timeout=timeout)
            return driver.find_element("css selector", selector)
    except Exception as e:
        logger.warning(f'Element not found or not visible: {selector}, Error: {e}')
        return None


# Test the PageParser if this file is executed directly
if __name__ == "__main__":
    from seleniumbase import Driver
    import time
    
    print('[PAGE_PARSER] Starting PageParser test...')
    
    # Initialize SeleniumBase driver
    driver = Driver(uc=True, headless=False)
    
    try:
        # Navigate to the test page (fixing the URL from the agent example)
        test_url = "https://www.google.com/search?sca_esv=eb0d7d55a8534e31&q=cute+puppies&source=lnms&fbs=AIIjpHw5plA02h2_1fIkdFlYLqY1Bgcn2vGJe8tyqFQkVN1wj3wg6jZNL_nJvzF0wXGdcz8B_0DxsT54JN7rQ7f6haWkqkGUVGkdalk-i2iV3t1n0Kcu0MPiCLVhvdIWoiGbEr6ecIt7g_Wjs0VsKpGOzYd_mY5oXLkDUXoF0SQV1W2bduduD9GrvsUJu3Ca3Nu4CEwo2rAUeKmoXhJ2oGBT7NRLvxLJTw&sa=X&ved=2ahUKEwjc3vvV0siQAxWpg_0HHf4CHqwQ0pQJegQIChAB&biw=1264&bih=745&dpr=1"
        print(f'[PAGE_PARSER] Navigating to: {test_url}')
        driver.get(test_url)
        
        # Wait for page to load
        time.sleep(3)
        
        # Write "   " in element #input-6
        print('[PAGE_PARSER] Writing text to #input-6...')
        # input_element = driver.find_element("css selector", "#input-6")
        # input_element.clear()
        # input_element.send_keys("   ")
        
        # # Click on the specified button
        # print('[PAGE_PARSER] Clicking button...')
        # button_selector = "#app > div > div > main > section > div.v-row.mt-8 > div.v-col-sm-5.v-col-12 > div.my-auto > div.v-row.mt-10 > div > button"
        # button_element = driver.find_element("css selector", button_selector)
        # button_element.click()
        
        # Wait for 30 seconds
        print('[PAGE_PARSER] Waiting 30 seconds...')
        # time.sleep(60)
        
        # Initialize PageParser
        parser = PageParser(driver)
        
        print('\n[PAGE_PARSER] Testing get_page_maps...')
        start_time = time.time()
        interactive_elements, interactive_string, content_elements, content_string = parser.get_page_maps()
        total_time = time.time() - start_time
        
        print(f'Found {len(interactive_elements)} interactive elements and {len(content_elements)} content elements in {total_time:.3f} seconds')
        
        # Save debug information to files
        import json
        import os
        
        debug_dir = 'output_debug'
        os.makedirs(debug_dir, exist_ok=True)
        
        # Save interactive elements as JSON
        interactive_data = []
        for elem in interactive_elements:
            interactive_data.append({
                'index': elem.index,
                'tag': elem.tag,
                'text': elem.text,
                'css_selector': elem.css_selector,
                'attributes': {
                    'id': elem.attributes.id,
                    'aria_label': elem.attributes.aria_label,
                    'placeholder': elem.attributes.placeholder,
                    'class_name': elem.attributes.class_name,
                    'value': elem.attributes.value,
                    'name': elem.attributes.name,
                    'type': elem.attributes.type,
                    'href': elem.attributes.href,
                    'title': elem.attributes.title
                }
            })
        
        with open(os.path.join(debug_dir, 'interactive_elements.json'), 'w', encoding='utf-8') as f:
            json.dump(interactive_data, f, indent=2, ensure_ascii=False)
        
        # Save content elements as JSON
        content_data = []
        for elem in content_elements:
            content_data.append({
                'index': elem.index,
                'tag': elem.tag,
                'text': elem.text,
                'css_selector': elem.css_selector,
                'attributes': {
                    'id': elem.attributes.id,
                    'aria_label': elem.attributes.aria_label,
                    'placeholder': elem.attributes.placeholder,
                    'class_name': elem.attributes.class_name,
                    'value': elem.attributes.value,
                    'name': elem.attributes.name,
                    'type': elem.attributes.type,
                    'href': elem.attributes.href,
                    'title': elem.attributes.title
                }
            })
        
        with open(os.path.join(debug_dir, 'content_elements.json'), 'w', encoding='utf-8') as f:
            json.dump(content_data, f, indent=2, ensure_ascii=False)
        
        # Save map strings
        with open(os.path.join(debug_dir, 'interactive_string.txt'), 'w', encoding='utf-8') as f:
            f.write(interactive_string)
        
        with open(os.path.join(debug_dir, 'content_string.txt'), 'w', encoding='utf-8') as f:
            f.write(content_string)
        
        print(f'\n[PAGE_PARSER] Debug files saved to {debug_dir}/')
        
        print('\nInteractive Map String (first 500 chars):')
        print(interactive_string[:500] + '...' if len(interactive_string) > 500 else interactive_string)
        
        print('\nContent Map String (first 500 chars):')
        print(content_string[:500] + '...' if len(content_string) > 500 else content_string)
        
        print('\n[PAGE_PARSER] Sample Interactive Elements:')
        for i, elem in enumerate(interactive_elements[:5]):  # Show first 5
            print(f'  [{elem.index}] {elem.tag}: "{elem.text[:50]}..." (CSS: {elem.css_selector})')
        
        print('\n[PAGE_PARSER] Sample Content Elements:')
        for i, elem in enumerate(content_elements[:5]):  # Show first 5
            print(f'  [{elem.index}] {elem.tag}: "{elem.text[:50]}..." (CSS: {elem.css_selector})')
        
        print('\n[PAGE_PARSER] Test completed successfully!')
        
    except Exception as error:
        print(f'[PAGE_PARSER] Error during test: {error}')
        
    finally:
        # Clean up
        print('[PAGE_PARSER] Closing browser...')
        driver.quit()