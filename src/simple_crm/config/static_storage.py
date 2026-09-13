"""Static storage policy for immutable, locally vendored runtime assets."""

from whitenoise.storage import CompressedManifestStaticFilesStorage


class CrmStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """Ignore optional upstream source-map comments during manifest collection.

    The Bootstrap and HTMX runtime files are verified byte-for-byte before
    collection. Their optional source maps are deliberately not runtime assets,
    so collecting production static files must not require them.
    """

    patterns = (
        (
            "*.css",
            (
                CompressedManifestStaticFilesStorage.patterns[0][1][0],
                CompressedManifestStaticFilesStorage.patterns[0][1][1],
            ),
        ),
    )
