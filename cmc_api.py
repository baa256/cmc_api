import requests
import pandas as pd

API_KEY = 'c380082d-3027-458a-8254-fa39469ebd3e'


class CoinMarketCapAPI:

    def __init__(self, api_key):
        self.session = requests.session()
        self.session.headers = {'X-CMC_PRO_API_KEY': api_key}


class CoinMarketCapData(CoinMarketCapAPI):
    def __init__(self,api_key):
        CoinMarketCapAPI.__init__(self,api_key)
        
        self.crypto_results = dict()
        self.metadata_results = dict()
        self.fcas_results = dict()

    def get_cryptocurrencies(self, symbols: list):
        missing_symbols = [symbol for symbol in symbols if symbol not in self.crypto_results]

        if missing_symbols:
            params = {'symbol': ','.join(missing_symbols),
                      'aux': 'num_market_pairs,cmc_rank,max_supply,circulating_supply,volume_7d,volume_30d'}
            r = api.session.get('https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest',
                                params=params)
            for symbol in missing_symbols:
                data = r.json()['data'][symbol]
                self.crypto_results[symbol] = data

        results = [self.crypto_results[symbol] for symbol in symbols]
        return results

    def get_top_cryptos(self, limit=100):
        params = {'listing_status': 'active',
                  'sort': 'cmc_rank',
                  'limit': limit}
        r = api.session.get('https://pro-api.coinmarketcap.com/v1/cryptocurrency/map',
                            params=params)
        data = r.json()['data']
        return data

    def get_metadata(self, symbols: list):
        missing_symbols = [symbol for symbol in symbols if symbol not in self.metadata_results]

        if missing_symbols:
            params = {'symbol': ','.join(missing_symbols),
                      'aux': 'tags,date_added'}
            r = api.session.get('https://pro-api.coinmarketcap.com/v1/cryptocurrency/info',
                                params=params)
            for symbol in missing_symbols:
                data = r.json()['data'][symbol]
                self.metadata_results[symbol] = data

        results = [self.metadata_results[symbol] for symbol in symbols]
        return results

    def get_fcas_scores(self, pages, limit=100):
        page = 0
        data = list()
        while page < pages:
            if page not in self.fcas_results:
                r = api.session.get(
                    'https://pro-api.coinmarketcap.com/v1/partners/flipside-crypto/fcas/listings/latest',
                    params={'start': (page * limit) + 1,
                            'limit': limit})

                self.fcas_results[page] = r.json()['data']

            data.append(self.fcas_results[page])
            page += 1

        return data

    def get_fcas_score(self, symbol):
        data = dict()

        if not self.fcas_results:
            raise Exception("need to init fcas scores on the api before searching for a symbol's score")

        for fcas_data in self.fcas_results.values():
            potential_data = [x for x in fcas_data if x['symbol'] == symbol]
            if potential_data:
                data = potential_data[0]
        return data


class Crypto(dict):

    def __init__(self, symbol, api: CoinMarketCapAPI):
        quote_data = api_data.get_cryptocurrencies([symbol])[0]
        metadata = api_data.get_metadata([symbol])[0]
        fcas_score_data = api_data.get_fcas_score(symbol)

        data = {
            'symbol': symbol,
            'cmc_rank': quote_data['cmc_rank'],
            'num_market_pairs': quote_data['num_market_pairs'],
            'max_supply': quote_data['max_supply'],
            'circulating_supply': quote_data['circulating_supply'],
            'price': quote_data['quote']['USD']['price'],
            'volume_24h': quote_data['quote']['USD']['volume_24h'],
            'volume_7d': quote_data['quote']['USD']['volume_7d'],
            'volume_30d': quote_data['quote']['USD']['volume_30d'],
            'market_cap': quote_data['quote']['USD']['market_cap'],
            'market_cap_dominance': quote_data['quote']['USD']['market_cap_dominance'],
            'category': metadata['category'],
            'tags': metadata['tags'] if metadata['tags'] else list(),
            'investment_partners': self._portofolio_count(metadata),
            'date_added': metadata['date_added'],
            'fcas_score': fcas_score_data.get('score', None),
            'fcas_grade': fcas_score_data.get('grade', None)
        }

        super().__init__(data)

    def contains_tag(self, tag):
        return tag in self.get('tags')

    @staticmethod
    def _portofolio_count(metadata):
        tags = metadata.get('tags')
        if not tags:
            tags = list()
        portfolio_tags = {tag for tag in tags if 'portfolio' in tag or 'capital' in tag}
        return len(portfolio_tags)


if __name__ == '__main__':
    api = CoinMarketCapAPI(API_KEY)
    api_data =CoinMarketCapData(api)
    
    # prime the api
    top_cryptos = api_data.get_top_cryptos(500)
    symbols = [x['symbol'] for x in top_cryptos]
    api_data.get_cryptocurrencies(symbols)
    api_data.get_metadata(symbols)
    api_data.get_fcas_scores(pages=10, limit=100)

    # create crypto dicts
    cryptos = list()
    for symbol in symbols:
        cryptos.append(Crypto(symbol, api))

    df = pd.DataFrame(cryptos)

    avg_max_supply_ratio = 6
    df['max_supply_calc'] = df['max_supply'].fillna(df['circulating_supply'] * avg_max_supply_ratio)
    df['avg_volume_7d'] = df['volume_7d'] / 7
    df['avg_volume_30d'] = df['volume_30d'] / 30

    df.to_csv('cryptos.csv', index=False)
    print('hold')
