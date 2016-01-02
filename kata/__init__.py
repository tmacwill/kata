def initialize(config):
    import kata.config
    kata.config.initialize(config)

    if kata.config.redis.__use__:
        import kata.cache
        kata.cache.initialize()

    if kata.config.database.__use__:
        import kata.db
        kata.db.initialize()
