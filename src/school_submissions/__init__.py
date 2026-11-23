__version__ = "1.3.0"

from .analysis_service import AnalysisService
from .comparison import PairSimilarity, compare_features, find_top_k
from .evaluation import (
    Corpus,
    ScoredPair,
    evaluate_corpus,
    load_corpus,
    render_markdown,
    select_threshold,
)
from .features import (
    AST_METHOD,
    FEATURE_VERSION,
    TOKEN_METHOD,
    FeatureSet,
    build_ast_features,
    build_features,
    build_token_features,
)
from .analyzers import (
    AnalysisContext,
    AnalysisReport,
    Analyzer,
    AnalyzerRegistry,
    LengthAnalyzer,
    TemplateAnalyzer,
)
from .models import Assignment, Submission
from .pipeline import FeatureStream, collect_features, index_size_bytes, iter_features
from .service import SubmissionService
from .sources import InMemorySource, JSONLSource, Source

__all__ = [
    "AnalysisContext",
    "AnalysisReport",
    "AnalysisService",
    "Analyzer",
    "AnalyzerRegistry",
    "AST_METHOD",
    "Corpus",
    "Assignment",
    "FEATURE_VERSION",
    "FeatureSet",
    "FeatureStream",
    "InMemorySource",
    "JSONLSource",
    "LengthAnalyzer",
    "PairSimilarity",
    "ScoredPair",
    "Source",
    "TOKEN_METHOD",
    "Submission",
    "SubmissionService",
    "TemplateAnalyzer",
    "build_ast_features",
    "build_features",
    "build_token_features",
    "collect_features",
    "evaluate_corpus",
    "compare_features",
    "find_top_k",
    "index_size_bytes",
    "iter_features",
    "load_corpus",
    "render_markdown",
    "select_threshold",
]
