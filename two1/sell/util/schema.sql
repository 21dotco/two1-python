create table services_stats (
    id integer primary key autoincrement,
    service text not null,
    buffer_earnings integer not null,
    wallet_earnings integer not null,
    channel_earnings integer not null,
    request_count integer not null,
    last_buy_time integer not null
);
