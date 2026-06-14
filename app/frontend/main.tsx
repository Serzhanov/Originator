import { StrictMode } from "react"
import * as ReactDOM from "react-dom/client"

import App from "./App.js"
import { Orpc } from "./orpc.js"

import "./styles.css"

const root = ReactDOM.createRoot(document.getElementById("root") as HTMLElement)

root.render(
  <StrictMode>
    <Orpc>
      <App />
    </Orpc>
  </StrictMode>
)
