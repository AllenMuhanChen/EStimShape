import inject

class DataService:
    def fetch_data(self):
        return "Data from the service"

class Client:
    @inject.autoparams()
    def __init__(self, data_service: DataService):
        self.data_service = data_service

    def work(self):
        data = self.data_service.fetch_data()
        print(f"Working with data: {data}")

def configuration(binder: inject.Binder) -> None:
    binder.bind(DataService, DataService())

inject.configure(configuration)

client = Client()  # Now the DataService dependency is automatically injected
client.work()
