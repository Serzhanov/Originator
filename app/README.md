# Excalidraw Application

## Overview

Self-hosted deployment of [Excalidraw](https://github.com/excalidraw/excalidraw), the open-source virtual whiteboard. Fully client-side — no server-side storage or collaboration backend.

## Architecture

- **Runtime**: Entirely client-side
- **State format**: Excalidraw's native JSON (scene elements + app state)

## Session Model

Sessions are fully self-contained and isolated:

- **Ephemeral by default**: All state lives in memory only. A page refresh resets to a blank canvas.
- **Optional persistence**: A persistence layer (e.g. blob storage) to save session snapshots somewhere would be a nice to have, but is not required.

## Window API

The app exposes two functions on `window` for external state control:

### `window.seed(json)`

Sets the project state from a JSON object.

- **Input**: Excalidraw scene JSON (`{ elements, appState, files }`)
- **Behavior**: Replaces the current canvas state with the provided scene
- **Returns**: `void`

### `window.getState()`

Returns the current project state as a JSON object.

- **Returns**: Excalidraw scene JSON (`{ elements, appState, files }`)
