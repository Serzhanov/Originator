"""Browser tool. Uses Playwright's page object."""

from __future__ import annotations

import base64
import json
from typing import Any

from playwright.sync_api import Page


class BrowserTool:
    def __init__(self, page: Page) -> None:
        self.page = page

    def execute(self, action: str, **kwargs: Any) -> dict[str, Any]:
        try:
            match action:
                case "navigate":
                    return self._navigate(kwargs["url"])
                case "screenshot":
                    return self._screenshot()
                case "zoom":
                    return self._zoom(kwargs["region"])
                case "left_click":
                    return self._click("left", 1, **kwargs)
                case "right_click":
                    return self._click("right", 1, **kwargs)
                case "middle_click":
                    return self._click("middle", 1, **kwargs)
                case "double_click":
                    return self._click("left", 2, **kwargs)
                case "triple_click":
                    return self._click("left", 3, **kwargs)
                case "left_click_drag":
                    return self._drag(kwargs.get("start_coordinate"), kwargs["coordinate"])
                case "left_mouse_down":
                    return self._mouse_down(kwargs["coordinate"])
                case "left_mouse_up":
                    return self._mouse_up(kwargs["coordinate"])
                case "type":
                    return self._type(kwargs["text"])
                case "key" | "press_key":
                    return self._press_key(kwargs["text"], kwargs.get("repeat", 1))
                case "hold_key":
                    return self._hold_key(kwargs["text"], kwargs["duration"])
                case "scroll":
                    return self._scroll(kwargs["coordinate"], kwargs["scroll_direction"], kwargs["scroll_amount"])
                case "scroll_to":
                    return self._scroll_to(kwargs["ref"])
                case "read_page":
                    return self._read_page(kwargs.get("filter"))
                case "get_page_text":
                    return self._get_page_text()
                case "wait":
                    return self._wait(kwargs["duration"])
                case "form_input":
                    return self._form_input(kwargs["ref"], kwargs["value"])
                case "create_tab" | "switch_tab" | "close_tab":
                    return self._error(f"{action} not supported in single-page mode")
                case "list_tabs":
                    return self._text("1 tab open")
                case _:
                    return self._error(f"Unknown action: {action}")
        except Exception as e:
            return self._error(f"Browser action failed: {e}")

    def _navigate(self, url: str) -> dict:
        self.page.goto(url, wait_until="domcontentloaded")
        return self._text(f"Navigated to {url}")

    def _screenshot(self) -> dict:
        data = self.page.screenshot()
        return {"content": [{"type": "image", "data": base64.b64encode(data).decode(), "mimeType": "image/png"}]}

    def _zoom(self, region: list[int]) -> dict:
        x0, y0, x1, y1 = region
        data = self.page.screenshot(clip={"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0})
        return {"content": [{"type": "image", "data": base64.b64encode(data).decode(), "mimeType": "image/png"}]}

    def _click(
        self,
        button: str,
        click_count: int,
        coordinate: list[int] | None = None,
        ref: str | None = None,
        selector: str | None = None,
        **_: Any,
    ) -> dict:
        if coordinate:
            x, y = coordinate
        elif ref or selector:
            q = f'[data-ref="{ref}"]' if ref else selector
            el = self.page.query_selector(q)
            if not el:
                return self._error("Element not found")
            box = el.bounding_box()
            if not box:
                return self._error("Element not visible")
            x = box["x"] + box["width"] / 2
            y = box["y"] + box["height"] / 2
        else:
            return self._error("coordinate, ref, or selector required")

        self.page.mouse.move(x, y)
        btn = button if button in ("left", "right", "middle") else "left"
        for _ in range(click_count):
            self.page.mouse.down(button=btn)
            self.page.mouse.up(button=btn)
        return self._text(f"Clicked at ({x}, {y})")

    def _drag(self, start: list[int] | None, end: list[int]) -> dict:
        sx, sy = (start or [0, 0])
        ex, ey = end
        self.page.mouse.move(sx, sy)
        self.page.mouse.down()
        self.page.mouse.move(ex, ey)
        self.page.mouse.up()
        return self._text(f"Dragged from ({sx}, {sy}) to ({ex}, {ey})")

    def _mouse_down(self, coordinate: list[int]) -> dict:
        x, y = coordinate
        self.page.mouse.move(x, y)
        self.page.mouse.down()
        return self._text(f"Mouse down at ({x}, {y})")

    def _mouse_up(self, coordinate: list[int]) -> dict:
        x, y = coordinate
        self.page.mouse.move(x, y)
        self.page.mouse.up()
        return self._text(f"Mouse up at ({x}, {y})")

    def _type(self, text: str) -> dict:
        self.page.keyboard.type(text)
        return self._text(f"Typed: {text[:50]}{'...' if len(text) > 50 else ''}")

    _KEY_MAP: dict[str, str] = {
        "enter": "Enter", "return": "Enter", "tab": "Tab",
        "escape": "Escape", "esc": "Escape", "backspace": "Backspace",
        "delete": "Delete", "space": "Space", "up": "ArrowUp",
        "down": "ArrowDown", "left": "ArrowLeft", "right": "ArrowRight",
        "home": "Home", "end": "End", "pageup": "PageUp", "pagedown": "PageDown",
    }

    def _press_key(self, text: str, repeat: int = 1) -> dict:
        keys = [self._KEY_MAP.get(k.lower(), k) for k in text.split()]
        for _ in range(repeat):
            for key in keys:
                self.page.keyboard.press(key)
        suffix = f" (repeated {repeat} times)" if repeat > 1 else ""
        return self._text(f"Pressed key(s): {text}{suffix}")

    def _hold_key(self, text: str, duration: float) -> dict:
        key = self._KEY_MAP.get(text.lower(), text)
        self.page.keyboard.down(key)
        self.page.wait_for_timeout(int(duration * 1000))
        self.page.keyboard.up(key)
        return self._text(f"Held {text} for {duration}s")

    def _scroll(self, coordinate: list[int], direction: str, amount: int) -> dict:
        x, y = coordinate
        pixels = amount * 100
        dx = {"left": -pixels, "right": pixels}.get(direction, 0)
        dy = {"up": -pixels, "down": pixels}.get(direction, 0)
        self.page.mouse.move(x, y)
        self.page.mouse.wheel(dx, dy)
        return self._text(f"Scrolled {direction} by {amount} at ({x}, {y})")

    def _scroll_to(self, ref: str) -> dict:
        self.page.evaluate(f"""
            (function() {{
                const el = document.querySelector('[data-ref="{ref}"]') || document.getElementById('{ref}');
                if (el) el.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
            }})()
        """)
        return self._text(f"Scrolled to element: {ref}")

    def _read_page(self, filter_: str | None = None) -> dict:
        result = self.page.evaluate(f"""
            (function() {{
                function getAccessibleTree(root, filter) {{
                    const results = [];
                    const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
                    let node = walker.currentNode;
                    while (node) {{
                        const el = node;
                        const isInteractive = el.matches('a, button, input, select, textarea, [onclick], [role="button"]');
                        if (!filter || filter === 'all' || (filter === 'interactive' && isInteractive)) {{
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) {{
                                results.push({{
                                    tag: el.tagName.toLowerCase(),
                                    text: el.textContent?.slice(0, 100) || '',
                                    role: el.getAttribute('role') || '',
                                    id: el.id || '',
                                }});
                            }}
                        }}
                        node = walker.nextNode();
                    }}
                    return results;
                }}
                return JSON.stringify({{
                    url: window.location.href,
                    title: document.title,
                    elements: getAccessibleTree(document.body, '{filter_ or ""}')
                }});
            }})()
        """)
        return self._text(result)

    def _get_page_text(self) -> dict:
        text = self.page.evaluate("document.body.innerText")
        if len(text) > 10000:
            text = text[:10000] + "..."
        return self._text(text)

    def _wait(self, duration: float) -> dict:
        self.page.wait_for_timeout(int(duration * 1000))
        return self._text(f"Waited {duration}s")

    def _form_input(self, ref: str, value: str) -> dict:
        result = self.page.evaluate(f"""
            (function() {{
                const el = document.querySelector('[data-ref="{ref}"]') || document.getElementById('{ref}');
                if (!el) return {{ success: false, message: 'Element not found' }};
                if (['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName)) {{
                    el.value = {json.dumps(value)};
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    return {{ success: true }};
                }}
                return {{ success: false, message: 'Not a form element' }};
            }})()
        """)
        if not result["success"]:
            return self._error(result.get("message", "Failed"))
        return self._text(f"Set value for {ref}")

    @staticmethod
    def _text(text: str) -> dict:
        return {"content": [{"type": "text", "text": text}]}

    @staticmethod
    def _error(message: str) -> dict:
        return {"content": [{"type": "text", "text": message}], "is_error": True}
