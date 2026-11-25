#!/bin/sh
set -eu

case " ${RENEWED_DOMAINS:-} " in
    *" maison-rest.duckdns.org "*) ;;
    *) exit 0 ;;
esac

/usr/bin/docker exec maison-test-nginx-1 nginx -t
/usr/bin/docker exec maison-test-nginx-1 nginx -s reload
