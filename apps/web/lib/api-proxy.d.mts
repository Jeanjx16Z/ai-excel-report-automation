type ProxyEnvironment = Record<string, string | undefined>;
export function proxyConfig(environment: ProxyEnvironment): {
  backendOrigin: string; frontendOrigin: string; secret: string;
};
export function forwardApi(
  request: Request, segments: string[], environment: ProxyEnvironment,
  fetcher?: typeof fetch,
): Promise<Response>;
