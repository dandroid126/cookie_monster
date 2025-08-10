container_name="cookie_monster"

function cleanup() {
  docker stop "$container_name"
  docker container rm --force "$container_name"
  echo "cleanup complete"
}

trap cleanup EXIT

docker build --tag "$container_name":dev . && \
docker run --rm --name "$container_name" -v ./.env:/app/.env -v ./out:/app/out localhost/"$container_name":dev
