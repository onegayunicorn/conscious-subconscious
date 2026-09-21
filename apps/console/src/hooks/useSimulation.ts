import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { ApiError, SimulationClient } from '../api/client';
import type {
  ApiMeta,
  MetricsSummary,
  ProvenanceSummary,
  SessionSnapshot,
  SimTick,
  TickPoint,
} from '../api/types';
import { downsample } from '../lib/format';

/** How many points the charts keep. A 72-hour run at dt=0.05 produces 1440. */
export const MAX_TICKS = 2000;

export type ConnectionState =
  | 'idle'
  | 'connecting'
  | 'streaming'
  | 'paused'
  | 'complete'
  | 'error'
  | 'offline';

export interface SimulationState {
  connection: ConnectionState;
  meta: ApiMeta | null;
  provenance: ProvenanceSummary | null;
  snapshot: SessionSnapshot | null;
  metrics: MetricsSummary | null;
  ticks: TickPoint[];
  error: string | null;
  /** Human-readable log lines. Deliberately short; this is not a debug console. */
  log: string[];
  runDigest: string | null;
}

const INITIAL: SimulationState = {
  connection: 'idle',
  meta: null,
  provenance: null,
  snapshot: null,
  metrics: null,
  ticks: [],
  error: null,
  log: [],
  runDigest: null,
};

export interface SimulationApi extends SimulationState {
  busy: boolean;
  /** Create a session and stream a batch of steps. */
  start: (options?: { scenario?: string; policy?: string; steps?: number }) => Promise<void>;
  /** Advance one step at a time. */
  stepOnce: (count?: number) => Promise<void>;
  /** Run the configured horizon to completion and fetch the summary. */
  runToCompletion: () => Promise<void>;
  /** Control the modelled attention directly. */
  focus: () => Promise<void>;
  release: () => Promise<void>;
  setPolicy: (policy: string) => Promise<void>;
  reset: () => void;
  /** Re-check connectivity without touching an existing session. */
  refreshMeta: () => Promise<void>;
}

/**
 * Owns the console's session lifecycle and tick buffer.
 *
 * Two behaviours are deliberate:
 *
 * * **A stream failure sets `offline`, it does not throw.** The console must stay
 *   usable — and keep showing the disclaimer and the provenance banner — when
 *   the service is not running.
 * * **The tick buffer is bounded.** A long run at a fine time step produces tens
 *   of thousands of points, and an unbounded array in React state is a slow
 *   memory leak that looks like a rendering bug.
 */
export function useSimulation(client: SimulationClient): SimulationApi {
  const [state, setState] = useState<SimulationState>(INITIAL);
  const [busy, setBusy] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const sessionRef = useRef<string | null>(null);

  const closeSocket = useCallback(() => {
    const socket = socketRef.current;
    if (socket !== null) {
      socketRef.current = null;
      socket.close();
    }
  }, []);

  useEffect(() => closeSocket, [closeSocket]);

  const appendLog = useCallback((line: string) => {
    setState((previous) => ({
      ...previous,
      log: [`${new Date().toLocaleTimeString()}  ${line}`, ...previous.log].slice(0, 60),
    }));
  }, []);

  const report = useCallback(
    (error: unknown) => {
      const message =
        error instanceof ApiError
          ? error.isAuthFailure
            ? 'The service requires an API key. Set VITE_API_KEY or run it on loopback.'
            : error.message
          : error instanceof Error
            ? error.message
            : 'Something went wrong.';
      setState((previous) => ({
        ...previous,
        error: message,
        connection: error instanceof ApiError && error.status === 0 ? 'offline' : 'error',
      }));
      appendLog(`error: ${message}`);
    },
    [appendLog],
  );

  const refreshMeta = useCallback(async () => {
    try {
      const [meta, parameters] = await Promise.all([client.meta(), client.parameters()]);
      setState((previous) => ({
        ...previous,
        meta,
        provenance: parameters.summary,
        error: null,
        connection: previous.connection === 'offline' ? 'idle' : previous.connection,
      }));
      appendLog(
        `connected: ${parameters.summary.unsupported} of ${parameters.summary.total} parameters lack empirical support`,
      );
    } catch (error) {
      report(error);
    }
  }, [appendLog, client, report]);

  const ingest = useCallback((tick: SimTick) => {
    const point: TickPoint = {
      t: tick.t_hours,
      integrity: tick.integrity,
      perceived: tick.perceived_progress ?? tick.integrity,
      attention: tick.attention ?? 1,
      focused: tick.focused ?? false,
    };
    setState((previous) => {
      const next = [...previous.ticks, point];
      return {
        ...previous,
        ticks: next.length > MAX_TICKS ? downsample(next, MAX_TICKS) : next,
      };
    });
  }, []);

  const start = useCallback(
    async (options: { scenario?: string; policy?: string; steps?: number } = {}) => {
      setBusy(true);
      closeSocket();
      try {
        const created = await client.createSession({
          ...(options.scenario !== undefined ? { scenario: options.scenario } : {}),
          ...(options.policy !== undefined
            ? { focus_policy: options.policy as 'never' | 'always' | 'intermittent' }
            : {}),
        });
        sessionRef.current = created.id;
        setState((previous) => ({
          ...previous,
          connection: 'connecting',
          snapshot: created.snapshot,
          ticks: [],
          metrics: null,
          runDigest: null,
          error: null,
          log: [`session ${created.id} created (scenario ${created.snapshot.scenario})`],
        }));

        const socket = client.stream(created.id, {
          steps: options.steps ?? 400,
          onTick: ingest,
          onError: (error) => report(error),
          onClose: () => {
            setState((previous) => ({
              ...previous,
              connection: previous.connection === 'error' ? 'error' : 'complete',
            }));
          },
        });
        socketRef.current = socket;
        setState((previous) => ({ ...previous, connection: 'streaming' }));
      } catch (error) {
        report(error);
      } finally {
        setBusy(false);
      }
    },
    [client, closeSocket, ingest, report],
  );

  const withSnapshot = useCallback(
    async (action: (id: string) => Promise<{ snapshot: SessionSnapshot }>) => {
      const id = sessionRef.current;
      if (id === null) {
        report(new Error('Start a session first.'));
        return;
      }
      setBusy(true);
      try {
        const outcome = await action(id);
        setState((previous) => ({ ...previous, snapshot: outcome.snapshot, error: null }));
      } catch (error) {
        report(error);
      } finally {
        setBusy(false);
      }
    },
    [report],
  );

  const stepOnce = useCallback(
    async (count = 1) => {
      const id = sessionRef.current;
      if (id === null) {
        report(new Error('Start a session first.'));
        return;
      }
      setBusy(true);
      try {
        const outcome = await client.step(id, count);
        setState((previous) => ({ ...previous, snapshot: outcome.snapshot, error: null }));
        for (let index = 0; index < count; index += 1) {
          ingest(outcome.state);
        }
      } catch (error) {
        report(error);
      } finally {
        setBusy(false);
      }
    },
    [client, ingest, report],
  );

  const runToCompletion = useCallback(async () => {
    closeSocket();
    await withSnapshot(async (id) => {
      await client.run(id);
      const [result, snapshot] = await Promise.all([client.result(id), client.snapshot(id)]);
      setState((previous) => ({
        ...previous,
        metrics: result.metrics,
        runDigest: result.digests.run,
        connection: 'complete',
      }));
      appendLog(`run complete; digest ${result.digests.run.slice(0, 16)}`);
      return { snapshot };
    });
  }, [appendLog, client, closeSocket, withSnapshot]);

  const focus = useCallback(
    () => withSnapshot(async (id) => client.command(id, { command: 'focus' })),
    [withSnapshot],
  );

  const release = useCallback(
    () => withSnapshot(async (id) => client.command(id, { command: 'release' })),
    [withSnapshot],
  );

  const setPolicy = useCallback(
    (policy: string) =>
      withSnapshot(async (id) => client.command(id, { command: 'set_policy', policy })),
    [withSnapshot],
  );

  const reset = useCallback(() => {
    closeSocket();
    sessionRef.current = null;
    setState((previous) => ({ ...INITIAL, meta: previous.meta, provenance: previous.provenance }));
  }, [closeSocket]);

  // Probe once on mount so the console can say "offline" rather than showing a
  // spinner forever when the service is not running.
  useEffect(() => {
    void refreshMeta();
  }, [refreshMeta]);

  return useMemo(
    () => ({
      ...state,
      busy,
      start,
      stepOnce,
      runToCompletion,
      focus,
      release,
      setPolicy,
      reset,
      refreshMeta,
    }),
    [
      busy,
      focus,
      refreshMeta,
      release,
      reset,
      runToCompletion,
      setPolicy,
      start,
      state,
      stepOnce,
    ],
  );
}
