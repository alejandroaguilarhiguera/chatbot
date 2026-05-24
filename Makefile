# QA
sam deploy --config-env qa

# Prod
sam deploy --config-env prod

# list events
sam local invoke ListEvents --event ./src/events/list_events.json --env-vars env.json