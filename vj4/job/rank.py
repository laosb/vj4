import collections
import logging

from vj4 import db
from vj4.model import builtin
from vj4.model import domain
from vj4.model import user
from vj4.util import argmethod
from vj4.util import domainjob


_logger = logging.getLogger(__name__)


@domainjob.wrap
async def run(domain_id: str, keyword: str='rp', rank_field: str='rank', level_field: str='level'):
  _logger.info('Ranking')
  uddocs = domain.get_multi_users(domain_id, fields={'uid': 1, keyword: 1}).sort(keyword, -1)
  last_uddoc = {keyword: None}
  rank = 0
  count = 0
  async for uddoc in uddocs:
    count += 1
    if keyword not in uddoc:
      uddoc[keyword] = None
    if uddoc[keyword] != last_uddoc[keyword]:
      rank = count
    await domain.set_user(domain_id, uddoc['uid'], **{rank_field: rank})
    last_uddoc = uddoc
    # progress
    if count % 1000 == 0:
      _logger.info('#{0}: Rank {1}'.format(count, rank))
  if rank == 0:
    _logger.warn('No one has {0}'.format(keyword))
    return
  if level_field:
    level_ranks = sorted([(level, round(int(count * perc / 100))) for level, perc in builtin.LEVELS.items()],
                         key=lambda i: i[1], reverse=True)
    assert level_ranks[0][1] == count
    for i in range(len(level_ranks) - 1):
      _logger.info('Updating users levelled {0}'.format(level_ranks[i][0]))
      await (db.Collection('domain.user')
             .update({'$and': [{rank_field: {'$lte': level_ranks[i][1]}},
                               {rank_field: {'$gt': level_ranks[i + 1][1]}}]},
                     {'$set': {level_field: level_ranks[i][0]}},
                     multi=True))
    i = len(level_ranks) - 1
    _logger.info('Updating users levelled {0}'.format(level_ranks[i][0]))
    await (db.Collection('domain.user')
           .update({rank_field: {'$lte': level_ranks[i][1]}},
                   {'$set': {level_field: level_ranks[i][0]}},
                   multi=True))


if __name__ == '__main__':
  argmethod.invoke_by_args()
