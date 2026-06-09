
schema = StructType([
    StructField("eventId", StringType()),
    StructField("userId", StringType()),
    StructField("productId", StringType()),
    StructField("category", StringType()),
    StructField("behavior", StringType()),
    StructField("score", IntegerType()),
    StructField("timestamp", StringType())
])

json_df = (
    df.selectExpr(
        "CAST(value AS STRING)"
    )
)

parsed_df = (
    json_df.select(
        from_json(
            col("value"),
            schema
        ).alias("data")
    )
    .select("data.*")
)

