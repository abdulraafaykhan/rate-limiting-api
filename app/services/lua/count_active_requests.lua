-- Expired owners do not count, even while other requests renew their slots.
local parts = redis.call('TIME')
local now = tonumber(parts[1]) + tonumber(parts[2]) / 1000000
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now)
return redis.call('ZCARD', KEYS[1])
