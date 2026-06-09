import json
import time

from kafka import KafkaProducer

from db_loader import DataLoader
from behavior_generator import (
    BehaviorGenerator
)


TOPIC = "user_behavior_events"


def main():

    print(
        "Loading data..."
    )

    loader = DataLoader()

    customers = (
        loader.load_customers()
    )

    (
        product_category_map,
        products_by_category,
        all_products

    ) = loader.load_products()

    print(
        f"Customers: {len(customers)}"
    )

    print(
        f"Products: {len(all_products)}"
    )

    print(
        f"Categories: "
        f"{len(products_by_category)}"
    )

    generator = (
        BehaviorGenerator(
            customers,
            product_category_map,
            products_by_category,
            all_products
        )
    )

    producer = KafkaProducer(

        bootstrap_servers=
            "localhost:9092",

        value_serializer=lambda v:
            json.dumps(v)
            .encode("utf-8")
    )

    print(
        "Start generating events..."
    )

    while True:

        event = (
            generator.generate_event()
        )

        producer.send(
            TOPIC,
            event
        )

        print(
            json.dumps(
                event,
                indent=2
            )
        )

        time.sleep(2)


if __name__ == "__main__":

    main()