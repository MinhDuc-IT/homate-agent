"""Document lifecycle and device metadata associated with the index."""


class DocumentCollection:
    def __init__(self, index, storage, devices):
        self.index, self.storage, self.devices = index, storage, devices

    def list(self, home_id): return self.index.list(home_id)

    def read(self, home_id, identifier):
        document = self.index.get(home_id, identifier)
        return self.storage.read(document['storage_key'])

    def delete(self, home_id, identifier):
        document = self.index.get(home_id, identifier)
        self.index.delete(home_id, identifier)
        self.storage.delete(document['storage_key'])

    def link(self, home_id, identifier, devices):
        self.devices.validate(devices)
        self.index.link(home_id, identifier, devices)
