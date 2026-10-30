-- KEYS[1]: owned leases, ARGV: maximum, TTL seconds, unique owner.
local now_parts = redis.call('TIME')
local now = tonumber(now_parts[1]) + tonumber(now_parts[2]) / 1000000
local ttl = tonumber(ARGV[2])
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now)
local count = redis.call('ZCARD', KEYS[1])
if count >= tonumber(ARGV[1]) then
    local first = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
    return {0, count, math.max(1, math.ceil(tonumber(first[2]) - now))}
end
redis.call('ZADD', KEYS[1], now + ttl, ARGV[3])
redis.call('EXPIRE', KEYS[1], math.ceil(ttl) + 1)
return {1, count + 1, 0}
