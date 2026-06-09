#!/bin/bash
# Monitor the uncapped CD8-OOD training+eval chain.
# Polls sacct and emits a wake sentinel whenever any job's state changes.
# Stops when all jobs are in a terminal state.
#
# Usage: ./monitor_uncapped_chain.sh <chain.csv>
#   chain.csv is a single line of "scgen_train,impact_train,scgen_eval,impact_eval"

set -euo pipefail

CHAIN_CSV="${1:-/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/scripts/.submitted_uncapped_a_ood_chain.csv}"
STATUS_LOG="/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/logs/uncapped_chain_status.log"
INTERVAL_SECONDS=60   # poll every minute
SENTINEL="AGENT_LOOP_WAKE_uncapped_chain"

mkdir -p "$(dirname "$STATUS_LOG")"

if [ ! -f "$CHAIN_CSV" ]; then
    echo "ERROR: chain file not found: $CHAIN_CSV" >&2
    exit 1
fi

JIDS=$(cat "$CHAIN_CSV" | tr ',' ' ')
JIDS_COMMA=$(cat "$CHAIN_CSV")
echo "monitoring JIDs: $JIDS" | tee -a "$STATUS_LOG"
echo "$(date -Iseconds) MONITOR_START jids=$JIDS_COMMA" >> "$STATUS_LOG"

# Terminal states (sacct reports them once jobs finish)
is_terminal() {
    case "$1" in
        COMPLETED|FAILED|CANCELLED|TIMEOUT|NODE_FAIL|PREEMPTED|BOOT_FAIL|DEADLINE|OUT_OF_MEMORY) return 0 ;;
        *) return 1 ;;
    esac
}

previous_state=""

while true; do
    # Query sacct for these JIDs only (parent records, no .batch / .extern).
    # Important: only fetch JobID + State so we compare on actual state changes,
    # not on Elapsed (which advances every second during RUNNING).
    state_table=$(sacct -j "$JIDS_COMMA" --noheader --parsable2 \
        --format=JobID,State \
        | grep -v '\.batch\|\.extern' || true)

    if [ -z "$state_table" ]; then
        echo "$(date -Iseconds) WARN: sacct returned empty; jobs may not be visible yet" >> "$STATUS_LOG"
        sleep "$INTERVAL_SECONDS"
        continue
    fi

    # Detect change since last poll
    if [ "$state_table" != "$previous_state" ]; then
        ts=$(date -Iseconds)
        echo "$ts STATE_CHANGE" >> "$STATUS_LOG"
        # Pretty-print with elapsed/exit for the log
        sacct -j "$JIDS_COMMA" --noheader --parsable2 \
            --format=JobID,JobName,State,Elapsed,ExitCode \
            | grep -v '\.batch\|\.extern' \
            | while IFS='|' read -r jid name state elapsed exit_code; do
                echo "  $jid $name $state elapsed=$elapsed exit=$exit_code" >> "$STATUS_LOG"
              done
        previous_state="$state_table"
        # Wake sentinel for the agent
        echo "$SENTINEL {\"prompt\":\"check uncapped chain status\"}"
    fi

    # Check whether all 4 jobs are in terminal state
    all_done=true
    while IFS='|' read -r jid state; do
        # State sometimes has trailing "+" or whitespace; strip
        state_clean=$(echo "$state" | tr -d '+ ')
        # CANCELLED can show as "CANCELLED by <uid>" — match prefix
        case "$state_clean" in
            CANCELLED*) state_clean="CANCELLED" ;;
        esac
        if ! is_terminal "$state_clean"; then
            all_done=false
            break
        fi
    done <<< "$state_table"

    if $all_done; then
        echo "$(date -Iseconds) ALL_DONE final_state:" >> "$STATUS_LOG"
        echo "$state_table" >> "$STATUS_LOG"
        echo "$SENTINEL {\"prompt\":\"all jobs done — check final results\"}"
        echo "monitor exit (all terminal)"
        exit 0
    fi

    sleep "$INTERVAL_SECONDS"
done
