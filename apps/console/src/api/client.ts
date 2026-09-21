import type {
  ApiMeta,
  CreateSessionBody,
  Envelope,
  ParameterRecord,
  ProvenanceSummary,
  RunResult,
  ScenarioRecord,
  SessionCreated,
  SessionSnapshot,
  SimTick,
} from './types';

/** An error carrying the HTTP status, so the UI can distinguish 401 from 500. */
export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }

  /** True when the request failed because the service refused the credentials. */
  get isAuthFailure(): boolean {
    return this.status === 401;
  }
}

export interface ClientOptions {
  /** Base URL of the service. Defaults to the `/api` dev-server proxy. */
  baseUrl?: string;
  /** Value for the `X-API-Key` header. Omit when the service runs on loopback. */
  apiKey?: string;
}

export interface StreamOptions {
  /** How many simulation steps to request. */
  steps?: number;
  /** Delay between ticks, in milliseconds. 0 streams as fast as the server can. */
  intervalMs?: number;
  onTick: (tick: SimTick, envelope: Envelope<SimTick>) => void;
  onError?: (error: Error) => void;
  onClose?: () => void;
}

/**
 * Thin client for the simulation service.
 *
 * Deliberately small and dependency-free: `fetch` for requests and the platform
 * `WebSocket` for streaming. Every method maps to one endpoint, so a reader can
 * check this file against `docs/api.md` in a minute.
 */
export class SimulationClient {
  private readonly baseUrl: string;
  private readonly apiKey: string | undefined;

  constructor(options: ClientOptions = {}) {
    const configured = options.baseUrl ?? import.meta.env.VITE_API_BASE ?? '/api';
    this.baseUrl = configured.replace(/\/+$/, '');
    const key = options.apiKey ?? import.meta.env.VITE_API_KEY;
    this.apiKey = key && key.length > 0 ? key : undefined;
  }

  /** True when the client is configured to present a key. */
  get hasApiKey(): boolean {
    return this.apiKey !== undefined;
  }

  private headers(extra: Record<string, string> = {}): Record<string, string> {
    const headers: Record<string, string> = { Accept: 'application/json', ...extra };
    if (this.apiKey !== undefined) {
      headers['X-API-Key'] = this.apiKey;
    }
    return headers;
  }

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    let response: Response;
    try {
      response = await fetch(`${this.baseUrl}${path}`, init);
    } catch (cause) {
      // A network failure and an HTTP failure need different messages: one means
      // "start the service", the other means "the service said no".
      throw new ApiError(0, 'Could not reach the simulation service.');
    }

    if (response.status === 204) {
      return undefined as T;
    }

    const text = await response.text();
    let parsed: unknown;
    try {
      parsed = text.length > 0 ? JSON.parse(text) : undefined;
    } catch {
      parsed = undefined;
    }

    if (!response.ok) {
      throw new ApiError(response.status, describeError(parsed, response.status));
    }
    return parsed as T;
  }

  // ------------------------------------------------------------- catalogue
  meta(): Promise<ApiMeta> {
    return this.request<ApiMeta>('/v1/meta', { headers: this.headers() });
  }

  parameters(unsupportedOnly = false): Promise<{
    summary: ProvenanceSummary;
    parameters: ParameterRecord[];
  }> {
    const query = unsupportedOnly ? '?unsupported_only=true' : '';
    return this.request('/v1/parameters' + query, { headers: this.headers() });
  }

  scenarios(): Promise<{ scenarios: ScenarioRecord[] }> {
    return this.request('/v1/scenarios', { headers: this.headers() });
  }

  // -------------------------------------------------------------- sessions
  createSession(body: CreateSessionBody = {}): Promise<SessionCreated> {
    return this.request<SessionCreated>('/v1/sessions', {
      method: 'POST',
      headers: this.headers({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(body),
    });
  }

  snapshot(sessionId: string): Promise<SessionSnapshot> {
    return this.request<SessionSnapshot>(`/v1/sessions/${encodeURIComponent(sessionId)}`, {
      headers: this.headers(),
    });
  }

  step(sessionId: string, count = 1): Promise<{ state: SimTick; snapshot: SessionSnapshot }> {
    return this.request(`/v1/sessions/${encodeURIComponent(sessionId)}/step`, {
      method: 'POST',
      headers: this.headers({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ count }),
    });
  }

  run(sessionId: string, hours?: number): Promise<RunResult> {
    return this.request<RunResult>(`/v1/sessions/${encodeURIComponent(sessionId)}/run`, {
      method: 'POST',
      headers: this.headers({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(hours === undefined ? {} : { hours }),
    });
  }

  command(
    sessionId: string,
    payload: { command: 'focus' | 'release' | 'set_policy'; target?: string; policy?: string },
  ): Promise<{ outcome: Record<string, unknown>; snapshot: SessionSnapshot }> {
    return this.request(`/v1/sessions/${encodeURIComponent(sessionId)}/commands`, {
      method: 'POST',
      headers: this.headers({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(payload),
    });
  }

  result(sessionId: string, includeSamples = false): Promise<RunResult> {
    const query = includeSamples ? '?include_samples=true' : '';
    return this.request<RunResult>(
      `/v1/sessions/${encodeURIComponent(sessionId)}/result${query}`,
      { headers: this.headers() },
    );
  }

  // ------------------------------------------------------------- streaming
  /** Absolute WebSocket URL for the session stream. */
  websocketUrl(sessionId: string): string {
    const path = `/ws/v1/sessions/${encodeURIComponent(sessionId)}`;
    const absolute = /^https?:\/\//i.test(this.baseUrl)
      ? this.baseUrl
      : `${globalThis.location?.origin ?? 'http://127.0.0.1:5173'}/api`;
    const url = new URL(absolute.replace(/^http/i, 'ws') + path);
    if (this.apiKey !== undefined) {
      // Browsers cannot set headers on a WebSocket handshake, so the key travels
      // as a query parameter. That is a real limitation, and it is why the key is
      // also accepted from the environment rather than only from a login form.
      url.searchParams.set('api_key', this.apiKey);
    }
    return url.toString();
  }

  /**
   * Open the tick stream. Returns the socket so the caller can close it.
   *
   * Errors are surfaced through `onError` rather than thrown, because a stream
   * failure arrives asynchronously and an unhandled rejection in a WebSocket
   * callback is invisible.
   */
  stream(sessionId: string, options: StreamOptions): WebSocket {
    const socket = new WebSocket(this.websocketUrl(sessionId));

    socket.addEventListener('open', () => {
      socket.send(
        JSON.stringify({
          command: 'step',
          steps: options.steps ?? 400,
          interval_ms: options.intervalMs ?? 0,
        }),
      );
    });

    socket.addEventListener('message', (event: MessageEvent<string>) => {
      let envelope: Envelope<SimTick | { detail?: string }>;
      try {
        envelope = JSON.parse(event.data) as Envelope<SimTick | { detail?: string }>;
      } catch {
        options.onError?.(new Error('The service sent a message that is not valid JSON.'));
        return;
      }
      if (envelope.type === 'error') {
        const detail = (envelope.payload as { detail?: string }).detail;
        options.onError?.(new Error(detail ?? 'The stream reported an error.'));
        return;
      }
      if (envelope.type === 'sim.tick') {
        options.onTick(envelope.payload as SimTick, envelope as Envelope<SimTick>);
      }
    });

    socket.addEventListener('error', () => {
      options.onError?.(new Error('The simulation stream failed.'));
    });

    socket.addEventListener('close', () => {
      options.onClose?.();
    });

    return socket;
  }
}

function describeError(parsed: unknown, status: number): string {
  if (parsed !== null && typeof parsed === 'object' && 'detail' in parsed) {
    const detail = (parsed as { detail: unknown }).detail;
    if (typeof detail === 'string') {
      return detail;
    }
    if (Array.isArray(detail)) {
      // FastAPI validation errors: surface the field, not the whole object.
      const first = detail[0] as { loc?: unknown[]; msg?: string } | undefined;
      const field = Array.isArray(first?.loc) ? first?.loc.slice(-1)[0] : undefined;
      return field ? `${String(field)}: ${first?.msg ?? 'invalid'}` : 'The request was rejected.';
    }
  }
  if (status === 401) {
    return 'The service refused the request: an API key is required.';
  }
  if (status === 429) {
    return 'Rate limited. Wait a moment and try again.';
  }
  return `The service returned HTTP ${status}.`;
}
