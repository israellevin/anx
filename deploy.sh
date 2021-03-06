#!/bin/bash
# Deploy the Anxiety Free server.

# Parse options
usage() { echo "Usage: $0 [s|shell] [t|test] [k|kill-listener] [r|run]"; }
if ! [ "$1" ]; then
    usage
    exit 1
fi
while [ "$1" ]; do
    case "$1" in
        s|shell)
            shell=1;;
        t|test)
            _test=1;;
        k|kill-listener)
            kill_listener=1;;
        r|run)
            run=1;;
        *)
            usage
            exit 0;;
    esac
    shift
done

# Get to the right dir.
pushd "$(dirname "${BASH_SOURCE[0]}")" > /dev/null

# Load environment.
. mkenv

if [ "$shell" ]; then
    echo -e "\n===  OPENING A PYTHON SHELL ===\n"
    python -ic "
import logs
logs.setup()
import db
import conversation as c"
fi

if [ "$_test" ]; then
    echo -e "\n===  TESTING ===\n"
    ANX_DEBUG=1 ANX_DB_NAME="${ANX_DB_NAME}_test" pytest ./test.py \
        -vlx --log-cli-level=0 --cov . --cov-report term-missing
    type pycodestyle && pycodestyle --max-line-length=120 *.py
    type pylint && pylint *.py
fi

if [ "$kill_listener" ]; then
    port=${ANX_PORT:-8000}
    signal=15
    while pids="$(lsof -i4TCP:$port -sTCP:LISTEN -t)"; do
        echo -e "\n===  FOUND EXISTING LISTENERS on port $port ===\n"
        xargs ps -fp <<<"$pids"
        read -n 1 -p"Kill current listeners? (Y/n) " q; echo
        if [ "$(tr '[:upper:]' '[:lower:]' <<<"$q")" = 'n' ]; then
            echo "Aborting"
            exit 1
        fi
        echo -e "\n===  KILLING LISTENERS on port $port ===\n"
        xargs kill -$signal <<<"$pids"
        sleep 1
        [ $signal = 15 ] && signal=2
        [ $signal = 2 ] && signal=1
        [ $signal = 1 ] && signal=9
    done
fi

if [ "$run" ]; then
    port=${ANX_PORT:-8000}
    [ -z "$kill_listener" ] && $0 kill-listener || exit 1
    echo -e "\n===  RUNNING WEB SERVER on 0.0.0.0:$port ===\n"
    if [ "$ANX_DEBUG" ] && [ "$ANX_DEBUG" != 0 ] && [ "$ANX_DEBUG" != n ]; then
        FLASK_APP=web FLASK_ENV=development flask run --host "0.0.0.0" --port $port &
        disown
    else
        uwsgi --http :$port --mount /anxwebserver=web:APP >/dev/null &
        disown
    fi
    sleep 1
    echo "Currently listening on port $port:"
    lsof -i4TCP:$port -sTCP:LISTEN -t | xargs ps -fp
fi
popd
