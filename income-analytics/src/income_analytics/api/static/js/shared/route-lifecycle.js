export function createRouteResource(loader) {
  let current = null;
  return {
    read() {
      if (!current) current = Promise.resolve().then(loader);
      return current;
    },
    invalidate() {
      current = null;
    },
  };
}

export function createRouteLifecycle({ loaders, globalLoader, beginCycle }) {
  let activeRoute = null;
  let activation = 0;
  return {
    get activeRoute() { return activeRoute; },
    async activate(route) {
      activeRoute = route;
      activation += 1;
      const currentActivation = activation;
      beginCycle?.();
      const routeLoader = loaders[route] || (() => Promise.resolve());
      const results = await Promise.allSettled([
        globalLoader ? globalLoader(route) : Promise.resolve(),
        routeLoader(),
      ]);
      return { route, current: currentActivation === activation, results };
    },
  };
}
