"""Regression checks for source anchor containment and provenance."""

import unittest

from audit_s6_4_preflight import Source, digest, symbol_regions, verify_record_anchors, verify_span


def anchor(source, anchor_id, symbol, first, last, start, end, role="PRIMARY"):
    return dict(
        AnchorId=anchor_id, RecordKind="MECHANISM", RecordId="TestRule", Role=role,
        SourceFile=source.path, StartLine=str(start), EndLine=str(end),
        SourceSpanSha256=digest("\n".join(source.lines[start - 1:end])),
        SourceFileSha256=source.sha256, SymbolKind="FUNCTION", Symbol=symbol,
        DeclarationLine=str(first), DefinitionEndLine=str(last),
        ScopeVerification="LEXICAL_DECLARATION_CONTAINMENT", RelationVerification="MANUAL_REVIEW",
    )


class SourceAnchorTest(unittest.TestCase):
    def setUp(self):
        self.source = Source("test.cpp", """\
bool model() {
    return true;
}
bool fallback() {
    // model is mentioned here as well.
    return false;
}
""")

    def verify(self, row, source=None):
        source = source or self.source
        verify_span(row, source, symbol_regions(source))

    def test_branch_does_not_need_function_name_on_its_line(self):
        self.verify(anchor(self.source, "A1", "model", 1, 3, 2, 2))

    def test_new_hash_cannot_validate_wrong_function(self):
        with self.assertRaisesRegex(ValueError, "outside"):
            self.verify(anchor(self.source, "A1", "model", 1, 3, 6, 6))

    def test_range_cannot_span_adjacent_functions(self):
        with self.assertRaisesRegex(ValueError, "outside"):
            self.verify(anchor(self.source, "A1", "model", 1, 3, 2, 4))

    def test_ambiguous_symbol_requires_resolution(self):
        overloaded = Source("overloaded.cpp", "int run(int x) { return x; }\nfloat run(float x) { return x; }\n")
        with self.assertRaisesRegex(ValueError, "expected one FUNCTION run"):
            self.verify(anchor(overloaded, "A1", "run", 1, 1, 1, 1), overloaded)

    def test_comment_does_not_prove_source(self):
        with self.assertRaisesRegex(ValueError, "no source code"):
            self.verify(anchor(self.source, "A1", "fallback", 4, 7, 5, 5))

    def test_supporting_content_is_checked(self):
        primary = anchor(self.source, "A1", "model", 1, 3, 2, 2)
        support = anchor(self.source, "A2", "fallback", 4, 7, 6, 6, "SUPPORTING")
        support["SourceSpanSha256"] = digest("different source text")
        record = dict(primary, MechanismId="TestRule", Function="model", SourceAnchorIds="A1;A2",
                      SupportingAnchors="A2")
        with self.assertRaisesRegex(ValueError, "A2: span hash drift"):
            verify_record_anchors([("MECHANISM", "MechanismId", [record])],
                                  {self.source.path: self.source}, [primary, support])

    def test_file_content_outside_anchor_still_has_hash(self):
        row = anchor(self.source, "A1", "model", 1, 3, 2, 2)
        changed = Source(self.source.path, self.source.raw + "// Outside the anchor.\n")
        with self.assertRaisesRegex(ValueError, "file hash drift"):
            self.verify(row, changed)


if __name__ == "__main__":
    unittest.main()
