# Native Dispatch Guard

A small Unix Python reference implementation for a common automation failure:
a controller times out, but the native application may still be running.
A second controller must not submit overlapping work merely because the first
controller returned or its process disappeared.

## Behavior

- A shared local file lock serializes cooperating controllers.
- Each request identifier is claimed once and retained on disk.
- Missing native completion leaves `outcome_unknown`, including after timeout.
- A completion marker must match both the attempt ID and request SHA-256.
- Reconciliation observes completion; it does not repeat the request.
- Native completion means the wrapper exited, not that outputs are correct or accepted.

## Run offline

Python 3.10+ on Unix; standard library only. From this directory:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 examples/simulate.py
```

The example prints `outcome_unknown`, `second dispatch blocked`, and
`native_finished`. It uses synthetic bytes and a temporary directory. It does
not launch a desktop application or call a provider.

## Integration contract

Create one `Guard` directory per shared native resource. All controllers must
cooperate using that same directory. Supply immutable request bytes describing
all required inputs, and a unique request identifier. The runner receives an
attempt record including the completion path. A trusted native wrapper must
write the exact `completion_payload(attempt)` only when the protected native
work has exited. If it starts asynchronous child work, returning from the
wrapper alone is not sufficient evidence of that child's completion.

Never call `write_completion` just to clear a timeout. The helper is for a
trusted completion producer or simulations. If a native request stops without
writing its marker, this minimal implementation remains blocked; it has no
automatic recovery, cancellation, process-killing, or operator-override API.

## Limits

This is a cooperative local coordination pattern, not distributed exactly-once
execution or a security boundary. Windows, network filesystems, hostile local
writers, multiple independent lock directories, and power-loss durability are
not supported/claimed. Request IDs are scoped to one guard directory. Claims
are retained indefinitely. Do not remove claims while work could still run.
Actual Photoshop, CAD, rendering, or other native integrations must implement
and test their own trustworthy completion markers.

Nine tests pass in the preparation environment, including a separate-process
lock test, late completion after timeout, incorrect markers, controller loss,
and corrupt state. No real native application was invoked by these tests.

## License

MIT. See the repository root LICENSE.
