from __future__ import print_function

from concurrent import futures
from moneywagon import get_address_balance, get_current_price

def fetch_wallet_balances(wallets, fiat, **modes):
    """
    Wallets must be list of two item lists. First item is crypto, second item
    is the address. example:

    [
        ['btc', '1PZ3Ps9RvCmUW1s1rHE25FeR8vtKUrhEai'],
        ['ltc', 'Lb78JDGxMcih1gs3AirMeRW6jaG5V9hwFZ']
    ]
    """
    price_fetch = set([x[0] for x in wallets])
    balances = {}
    prices = {}

    fetch_length = len(wallets) + len(price_fetch)

    if not modes.get('async', False):
        # synchronous fetching
        for crypto in price_fetch:
            prices[crypto] = get_current_price(crypto, fiat, report_services=True, **modes)

        for crypto, address in wallets:
            balances[address] = get_address_balance(crypto, address.strip(), **modes)

    else:
        # asynchronous fetching
        if modes.get('verbose', False):
            print("Need to make", fetch_length, "external calls")

        with futures.ThreadPoolExecutor(max_workers=int(fetch_length / 2)) as executor:
            future_to_key = dict(
                (executor.submit(
                    get_current_price, crypto, fiat, report_services=True, **modes
                ), crypto) for crypto in price_fetch
            )

            future_to_key.update(dict(
                (executor.submit(
                    get_address_balance, crypto, address.strip(), **modes
                ), address) for crypto, address in wallets
            ))

            done, not_done = futures.wait(future_to_key, return_when=futures.FIRST_EXCEPTION)
            if len(not_done) > 0:
                raise not_done.pop().exception()

            for future in done:
                key = future_to_key[future]
                if len(key) > 5: # this will break if a crypto symbol is longer than 5 chars.
                    which = balances
                else:
                    which = prices

                res = future.result()
                which[key] = res

    ret = []

    for crypto, address in wallets:
        crypto_value = balances[address]
        sources, fiat_price = prices[crypto]
        ret.append({
            'crypto': crypto,
            'address': address,
            'crypto_value': crypto_value,
            'fiat_value': crypto_value * fiat_price,
            'conversion_price': fiat_price,
            'price_source': sources[0].name
        })

    return ret
