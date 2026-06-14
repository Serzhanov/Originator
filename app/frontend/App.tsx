import { Excalidraw } from "@excalidraw/excalidraw"

import "@excalidraw/excalidraw/index.css"

import type { OrderedExcalidrawElement } from "@excalidraw/excalidraw/element/types"
import type { AppState, BinaryFiles, ExcalidrawImperativeAPI } from "@excalidraw/excalidraw/types"
import * as React from "react"

import { useOrpc } from "./orpc.js"

interface SceneState {
  elements: readonly OrderedExcalidrawElement[]
  appState: AppState
  files: BinaryFiles
}

declare global {
  interface Window {
    seed?: (json: Partial<SceneState>) => Promise<void>
    getState?: () => SceneState
  }
}

// Prepare appState for updateScene — fix values that don't survive JSON round-trips
// (e.g. collaborators must be a Map, not a plain object)
// Prepare appState for updateScene — fix values that don't survive JSON round-trips
// (e.g. collaborators must be a Map, not a plain object).
// Returns a type compatible with updateScene's generic Pick<AppState, K> parameter.
function sanitizeAppState(raw: Partial<AppState>): AppState {
  const out = { ...raw }
  if (out.collaborators && !(out.collaborators instanceof Map)) {
    out.collaborators = new Map(
      Object.entries(out.collaborators as unknown as Record<string, unknown>)
    ) as AppState["collaborators"]
  }
  return out as AppState
}

const App: React.FC = () => {
  const { client } = useOrpc()
  const [excalidrawAPI, setExcalidrawAPI] = React.useState<ExcalidrawImperativeAPI | null>(null)

  // Fetch initial state on mount
  React.useEffect(() => {
    if (!excalidrawAPI) return

    client._control
      .getState()
      .then(state => {
        if (state.elements.length > 0) {
          excalidrawAPI.updateScene({
            elements: state.elements as unknown as OrderedExcalidrawElement[],
            appState: sanitizeAppState(state.appState as Partial<AppState>),
          })
          setTimeout(() => {
            excalidrawAPI.scrollToContent(undefined, { fitToContent: true, animate: false })
          }, 0)
        }
      })
      .catch(console.error)
  }, [excalidrawAPI, client])

  // Expose window.seed and window.getState
  React.useEffect(() => {
    if (!excalidrawAPI) return

    window.seed = async (json: Partial<SceneState>) => {
      const elements = json.elements ?? []
      const appState = json.appState ?? ({} as AppState)
      const files = json.files ?? {}

      await client._control.seed({
        events: [
          {
            type: "sceneUpdated",
            elements: elements as unknown as Record<string, unknown>[],
            appState: appState as unknown as Record<string, unknown>,
            files: files as unknown as Record<string, unknown>,
          },
        ],
      })

      excalidrawAPI.updateScene({
        elements,
        appState: sanitizeAppState(appState),
      })

      if (json.files && Object.keys(json.files).length > 0) {
        excalidrawAPI.addFiles(Object.values(json.files))
      }

      setTimeout(() => {
        excalidrawAPI.scrollToContent(undefined, { fitToContent: true, animate: false })
      }, 0)
    }

    window.getState = () => {
      const appState = excalidrawAPI.getAppState()
      const elements = [...excalidrawAPI.getSceneElements()]
      // Include any text element currently in creation/edit mode
      const newEl = (appState as any).newElement
      if (newEl && newEl.type === "text" && (newEl.text ?? "").trim()) {
        elements.push(newEl)
      }
      return { elements, appState, files: excalidrawAPI.getFiles() }
    }

    return () => {
      delete window.seed
      delete window.getState
    }
  }, [excalidrawAPI, client])

  const onChange = React.useCallback(
    (elements: readonly OrderedExcalidrawElement[], appState: AppState, files: BinaryFiles) => {
      client._control
        .seed({
          events: [
            {
              type: "sceneUpdated" as const,
              elements: JSON.parse(JSON.stringify(elements)) as Record<string, unknown>[],
              appState: JSON.parse(JSON.stringify(appState)) as Record<string, unknown>,
              files: JSON.parse(JSON.stringify(files)) as Record<string, unknown>,
            },
          ],
        })
        .catch(e => {
          console.log(e)
        })
    },
    [client]
  )

  return (
    <div style={{ width: "100vw", height: "100vh" }}>
      <Excalidraw excalidrawAPI={setExcalidrawAPI} onChange={onChange} initialData={{ elements: [], appState: {}, files: {} }} />
    </div>
  )
}

export default App
