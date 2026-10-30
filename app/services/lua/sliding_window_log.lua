-- Sliding Window Log: keep the timestamp of every recent request.
-- A request is allowed only if fewer than `limit` timestamps are inside
-- the last `window_seconds`.
--
-- Redis runs this whole script as ONE atomic step, so 100 simultaneous
-- requests can never slip past the limit through a race condition.
--
-- KEYS[2] = saved admin quota
-- KEYS[1] = sorted set that stores the request timestamps of one user
-- ARGV[1] = limit (max requests inside the window)
-- ARGV[2] = window_seconds
-- ARGV[3] = should_consume (1 = count this request, 0 = only look)
-- ARGV[4] = request_id (unique text so two requests never collide)
--
-- Returns: {allowed, remaining, retry_after, limit, window_seconds}

local limit = tonumber(ARGV[1])
local window_seconds = tonumber(ARGV[2])
-- Read the current admin quota inside the atomic check, so a request
-- carrying an older Python snapshot cannot use it after reconfiguration.
local configured = redis.call('HMGET', KEYS[2], 'limit', 'window_seconds', 'algorithm')
if configured[1] then
    limit = tonumber(configured[1])
    window_seconds = tonumber(configured[2])
end
-- Reject stale dispatch before touching state for the wrong algorithm.
if configured[3] and configured[3] ~= '' and configured[3] ~= 'sliding_window_log' then
    return {-1, 0, 0, 0, 0}
end
local should_consume = tonumber(ARGV[3])
local request_id = ARGV[4]

-- Use the clock of Redis itself, so every API copy agrees on the time.
local redis_time = redis.call('TIME')
local now = tonumber(redis_time[1]) + tonumber(redis_time[2]) / 1000000

-- Forget requests that are older than the window; they no longer count.
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - window_seconds)

-- Count the requests still inside the window.
local used = redis.call('ZCARD', KEYS[1])

-- There is room: allow the request.
if used < limit then
    if should_consume == 1 then
        -- Record this request with its timestamp as the score.
        redis.call('ZADD', KEYS[1], now, request_id)
        -- Let Redis delete the key by itself when the user goes quiet.
        redis.call('EXPIRE', KEYS[1], math.ceil(window_seconds))
        used = used + 1
    end
    return {1, limit - used, 0, limit, window_seconds, tostring(now)}
end

-- No room: the oldest request decides when space opens up again.
local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
local retry_after = math.ceil(tonumber(oldest[2]) + window_seconds - now)

-- Never tell the client to retry in 0 seconds.
if retry_after < 1 then
    retry_after = 1
end

return {0, 0, retry_after, limit, window_seconds, tostring(now)}
