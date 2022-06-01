### Bugfixes

* Fix behavior of `globus api` to respect formatting options. `--jmespath` can
  be used on results, and `-Fjson` will pretty-print JSON responses if the
  original response body is compact JSON
