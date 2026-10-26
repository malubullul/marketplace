import { hydrateRoot } from "react-dom/client";
import ErrorBlockDemo from "./demo";

const root = document.getElementById("error-page");
if (root) hydrateRoot(root, <ErrorBlockDemo />);
