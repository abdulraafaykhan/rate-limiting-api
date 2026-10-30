-- Renew only an owned, still-valid lease. Never resurrect expired work.
local parts = redis.call('TIME')
local now = tonumber(parts[1]) + tonumber(parts[2]) / 1000000
local expires = redis.call('ZSCORE', KEYS[1], ARGV[1])
if not expires or tonumber(expires) <= now then
    return 0
end
local ttl = tonumber(ARGV[2])
redis.call('ZADD', KEYS[1], 'XX', now + ttl, ARGV[1])
redis.call('EXPIRE', KEYS[1], math.ceil(ttl) + 1)
return 1
