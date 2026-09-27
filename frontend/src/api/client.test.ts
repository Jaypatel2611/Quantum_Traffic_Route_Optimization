import { describe, it, expect, vi, beforeEach } from 'vitest';
import { subscribeToConvergence } from './client';

class FakeEventSource {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSED = 2;

  readyState = FakeEventSource.OPEN;
  listeners: Record<string, ((event: unknown) => void)[]> = {};
  closed = false;

  addEventListener(type: string, handler: (event: unknown) => void) {
    (this.listeners[type] ??= []).push(handler);
  }
  close() {
    this.closed = true;
  }
  emit(type: string, event: unknown) {
    this.listeners[type]?.forEach((handler) => handler(event));
  }
}

describe('subscribeToConvergence', () => {
  let fakeSource: FakeEventSource;

  beforeEach(() => {
    fakeSource = new FakeEventSource();
    function MockEventSource() {
      return fakeSource;
    }
    const constructor = Object.assign(MockEventSource, {
      CONNECTING: FakeEventSource.CONNECTING,
      OPEN: FakeEventSource.OPEN,
      CLOSED: FakeEventSource.CLOSED,
    });
    vi.stubGlobal('EventSource', constructor as unknown as typeof EventSource);
  });

  it('routes progress events to onProgress', () => {
    const onProgress = vi.fn();
    subscribeToConvergence('job1', { onProgress, onComplete: vi.fn(), onError: vi.fn() });

    fakeSource.emit('progress', { data: JSON.stringify({ gbest: 0.42 }) });
    expect(onProgress).toHaveBeenCalledWith(0.42);
  });

  it('closes the stream and calls onComplete on a complete event', () => {
    const onComplete = vi.fn();
    subscribeToConvergence('job1', { onProgress: vi.fn(), onComplete, onError: vi.fn() });

    fakeSource.emit('complete', {});
    expect(onComplete).toHaveBeenCalled();
    expect(fakeSource.closed).toBe(true);
  });

  it('treats a named backend error event as terminal', () => {
    const onError = vi.fn();
    subscribeToConvergence('job1', { onProgress: vi.fn(), onComplete: vi.fn(), onError });

    fakeSource.emit('error', { data: JSON.stringify({ detail: 'solver crashed' }) });
    expect(onError).toHaveBeenCalledWith('solver crashed');
    expect(fakeSource.closed).toBe(true);
  });

  it('ignores a transient connection-level error while still reconnecting', () => {
    const onError = vi.fn();
    subscribeToConvergence('job1', { onProgress: vi.fn(), onComplete: vi.fn(), onError });

    fakeSource.readyState = FakeEventSource.CONNECTING;
    fakeSource.emit('error', {});
    expect(onError).not.toHaveBeenCalled();
    expect(fakeSource.closed).toBe(false);
  });

  it('reports a connection error once the browser has given up reconnecting', () => {
    const onError = vi.fn();
    subscribeToConvergence('job1', { onProgress: vi.fn(), onComplete: vi.fn(), onError });

    fakeSource.readyState = FakeEventSource.CLOSED;
    fakeSource.emit('error', {});
    expect(onError).toHaveBeenCalledWith('connection lost');
  });
});
