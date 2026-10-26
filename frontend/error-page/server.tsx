import { renderToString } from "react-dom/server";
import ErrorBlockDemo from "./demo";

export function render() {
  return renderToString(<ErrorBlockDemo />);
}
