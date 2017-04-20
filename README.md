# target-magentobi

Reads [Singer](https://singer.io) formatted data from stdin and persists it to the [Magento Business Intelligence Import API](http://developers.rjmetrics.com/).

## Install

Requires Python 3

```bash
› pip install target-magentobi
```

## Use

target-magentobi takes two types of input:

1. A config file containing your Magento BI client id and api key
2. A stream of Singer-formatted data on stdin

Create config file to contain your Magento BI client id and api key:

```json
{
  "client_id" : 1234,
  "api_key" : "29951bc00008626893bb92cd2a1234d3"
}
```

```bash
› tap-some-api | target-magentobi --config config.json
```

where `tap-some-api` is [Singer Tap](https://singer.io).

