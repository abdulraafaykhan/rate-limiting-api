-- Token Bucket: each user owns a bucket that holds up to `capacity` tokens.
-- Every request takes one token. Tokens drip back at a steady rate, so a
-- user may burst up to `capacity` and is then smoothed to the refill rate.
--
-- Redis runs this whole script as ONE atomic step (no race conditions).
--
-- KEYS[2] = saved admin quota
-- KEYS[1] = hash that stores the bucket of one user
-- ARGV[1] = capacity (same number as the user's limit)
-- ARGV[2] = window_seconds (a full refill takes this long)
-- ARGV[3] = should_consume (1 = take a token, 0 = only look)
--
-- Returns: {allowed, remaining, retry_after, limit, window_seconds}

local capacity = tonumber(ARGV[1])
local window_seconds = tonumber(ARGV[2])
-- Read the current admin quota inside the atomic check, so a request
-- carrying an older Python snapshot cannot use it after reconfiguration.
local configured = redis.call('HMGET', KEYS[2], 'limit', 'window_seconds', 'algorithm')
if configured[1] then
    capacity = tonumber(configured[1])
    window_seconds = tonumber(configured[2])
end
-- Reject stale dispatch before touching state for the wrong algorithm.
if configured[3] and configured[3] ~= '' and configured[3] ~= 'token_bucket' then
    return {-1, 0, 0, 0, 0}
end
local should_consume = tonumber(ARGV[3])

-- Tokens added per second, so an empty bucket refills in `window_seconds`.
local refill_per_second = capacity / window_seconds

-- Use the clock of Redis itself, so every API copy agrees on the time.
local redis_time = redis.call('TIME')
local now = tonumber(redis_time[1]) + tonumber(redis_time[2]) / 1000000

-- Load the saved bucket (both values are missing for a new user).
local saved = redis.call('HMGET', KEYS[1], 'tokens', 'last_refill_time')
local tokens = tonumber(saved[1])
local last_refill_time = tonumber(saved[2])

-- A brand new user starts with a full bucket.
if tokens == nil then
    tokens = capacity
    last_refill_time = now
end

-- Add the tokens earned since the last visit, but never above capacity.
local seconds_passed = math.max(0, now - last_refill_time)
tokens = math.min(capacity, tokens + seconds_passed * refill_per_second)

local allowed = 0
local retry_after = 0

if tokens >= 1 then
    -- At least one whole token is available: allow the request.
    allowed = 1
    if should_consume == 1 then
        tokens = tokens - 1
    end
else
    -- Not enough tokens: compute how long until one full token exists.
    retry_after = math.ceil((1 - tokens) / refill_per_second)
end

-- Save the new state only when this call is a real request.
if should_consume == 1 then
    redis.call('HSET', KEYS[1], 'tokens', tokens, 'last_refill_time', now)
    -- After a full refill the bucket equals a new one, so it can expire.
    redis.call('EXPIRE', KEYS[1], math.ceil(window_seconds) + 1)
end

return {allowed, math.floor(tokens), retry_after, capacity, window_seconds, tostring(now)}
