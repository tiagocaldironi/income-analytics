import { portfolioApi } from "../api.js";
import { createRouteResource } from "./route-lifecycle.js";

const intelligence = createRouteResource(() => portfolioApi.intelligence());

export const sharedIntelligence = () => intelligence.read();
export const invalidateSharedIntelligence = () => intelligence.invalidate();
export const beginRouteResourceCycle = () => intelligence.invalidate();
