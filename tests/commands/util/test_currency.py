"""Unit tests for currency utilities."""
from two1.commands.util import currency
from two1.commands.util.currency import Price

BTC_TO_USD = 450


def mock_get_usd_rate(self, amount=1e8):
    """Mock for the rest client's exchange rate functionality."""
    return amount * BTC_TO_USD / 1e8


def test_convert_satoshis_to_btc(mock_rest_client):
    """It should convert between satoshis and BTC and vice versa."""
    sat = Price(10000, Price.SAT, mock_rest_client)
    btc = sat.bitcoins
    assert sat.denomination == Price.SAT
    assert btc == 10000 / 1e8

    new_btc = Price(btc, Price.BTC, mock_rest_client)
    new_sat = new_btc.satoshis
    assert new_btc.denomination == Price.BTC
    assert new_sat == 10000


def test_convert_dollars_to_btc(mock_rest_client):
    """It should convert between US Dollars and BTC and vice versa."""
    setattr(Price, "_get_usd_rate", mock_get_usd_rate)

    sat = Price(10000, Price.SAT, mock_rest_client)
    usd = sat.usd
    assert sat.denomination == Price.SAT
    assert usd == .045

    new_usd = Price(usd, Price.USD, mock_rest_client)
    new_sat = new_usd.satoshis
    assert new_usd.denomination == Price.USD
    assert round(new_sat) == 10000


def test_shorthand_conversion(mock_rest_client):
    """It should make conversions with properties."""
    setattr(Price, "_get_usd_rate", mock_get_usd_rate)

    price = Price(100000, rest_client=mock_rest_client)
    assert price.satoshis == 100000
    assert price.bitcoins == 0.001
    assert price.usd == 0.45

    price = Price(.001, Price.BTC, mock_rest_client)
    assert price.satoshis == 100000
    assert price.bitcoins == 0.001
    assert price.usd == 0.45

    price = Price(900, Price.USD, mock_rest_client)
    assert price.usd == 900
    assert price.bitcoins == 2
    assert price.satoshis == 2e8

    price = Price(5, Price.USD, mock_rest_client)
    assert price.usd == 5.00
    assert round(price.bitcoins, 8) == 0.01111111
    assert round(price.satoshis) == 1111111


def test_exchange_rates(monkeypatch, mock_rest_client):
    """It should have general exchange rates."""
    monkeypatch.setattr(currency, "create_default_rest_client", lambda: mock_rest_client)
    setattr(Price, "_get_usd_rate", mock_get_usd_rate)

    assert Price.exchange_rate(Price.SAT, Price.BTC) == 1 / 1e8
    assert Price.exchange_rate(Price.BTC, Price.SAT) == 1e8
    assert Price.exchange_rate(Price.USD, Price.BTC) == round(1 / BTC_TO_USD, 8)
    assert Price.exchange_rate(Price.BTC, Price.USD) == BTC_TO_USD
    assert Price.exchange_rate(Price.USD, Price.SAT) == round(1e8 / BTC_TO_USD)
    assert Price.exchange_rate(Price.SAT, Price.USD) == BTC_TO_USD / 1e8
