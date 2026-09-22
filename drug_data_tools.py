from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent


# =========================================================
# 데이터 불러오기
# =========================================================
def load_data():

    drug_path = (
        BASE_DIR
        / "drug_data.csv"
    )

    ingredient_path = (
        BASE_DIR
        / "ingredient_data.csv"
    )


    if not drug_path.exists():

        raise FileNotFoundError(
            "drug_data.csv 파일이 없습니다."
        )


    if not ingredient_path.exists():

        raise FileNotFoundError(
            "ingredient_data.csv 파일이 없습니다."
        )


    drug_data = pd.read_csv(
        drug_path
    )

    ingredient_data = pd.read_csv(
        ingredient_path
    )


    # 필요한 열 확인
    required_drug_cols = {
        "제품명",
        "제조사",
        "카테고리",
        "성분",
    }

    required_ingredient_cols = {
        "성분명",
        "분류",
        "설명",
    }


    if not required_drug_cols.issubset(
        drug_data.columns
    ):

        missing = (
            required_drug_cols
            - set(drug_data.columns)
        )

        raise ValueError(
            "drug_data.csv에 "
            f"필요한 열이 없습니다: {missing}"
        )


    if not required_ingredient_cols.issubset(
        ingredient_data.columns
    ):

        missing = (
            required_ingredient_cols
            - set(
                ingredient_data.columns
            )
        )

        raise ValueError(
            "ingredient_data.csv에 "
            f"필요한 열이 없습니다: {missing}"
        )


    # 문자열 공백 정리
    for col in [
        "제품명",
        "제조사",
        "카테고리",
        "성분",
    ]:

        drug_data[col] = (
            drug_data[col]
            .astype(str)
            .str.strip()
        )


    for col in [
        "성분명",
        "분류",
        "설명",
    ]:

        ingredient_data[col] = (
            ingredient_data[col]
            .astype(str)
            .str.strip()
        )


    return (
        drug_data,
        ingredient_data,
    )


# =========================================================
# 성분 문자열 분리
# =========================================================
def split_ingredients(
    ingredient_text
):

    return [
        ingredient.strip()

        for ingredient
        in str(
            ingredient_text
        ).split("|")

        if ingredient.strip()
    ]


# =========================================================
# 선택한 약
# =========================================================
def get_selected_drugs(
    drug_data,
    selected_names,
):

    return drug_data[
        drug_data[
            "제품명"
        ].isin(
            selected_names
        )
    ].copy()


# =========================================================
# 중복 성분 분석
# =========================================================
def find_duplicates(
    selected_drugs
):

    ingredient_map = {}


    for _, row in (
        selected_drugs.iterrows()
    ):

        drug_name = (
            row["제품명"]
        )


        for ingredient in (
            split_ingredients(
                row["성분"]
            )
        ):

            ingredient_map.setdefault(
                ingredient,
                set(),
            ).add(
                drug_name
            )


    duplicates = {

        ingredient:
            sorted(products)

        for ingredient, products
        in ingredient_map.items()

        if len(products) >= 2
    }


    return (
        duplicates,
        ingredient_map,
    )


# =========================================================
# 약 검색
# =========================================================
def search_drugs(
    drug_data,
    keyword,
):

    keyword = keyword.strip()


    if not keyword:

        return pd.DataFrame()


    mask = (

        drug_data[
            "제품명"
        ].str.contains(
            keyword,
            case=False,
            na=False,
            regex=False,
        )

        |

        drug_data[
            "제조사"
        ].str.contains(
            keyword,
            case=False,
            na=False,
            regex=False,
        )

        |

        drug_data[
            "카테고리"
        ].str.contains(
            keyword,
            case=False,
            na=False,
            regex=False,
        )

        |

        drug_data[
            "성분"
        ].str.contains(
            keyword,
            case=False,
            na=False,
            regex=False,
        )
    )


    return drug_data[
        mask
    ].copy()


# =========================================================
# 성분 검색
# =========================================================
def search_ingredient(
    ingredient_data,
    drug_data,
    keyword,
):

    keyword = keyword.strip()


    if not keyword:

        return pd.DataFrame()


    mask = (

        ingredient_data[
            "성분명"
        ].str.contains(
            keyword,
            case=False,
            na=False,
            regex=False,
        )

        |

        ingredient_data[
            "분류"
        ].str.contains(
            keyword,
            case=False,
            na=False,
            regex=False,
        )
    )


    result = (
        ingredient_data[
            mask
        ].copy()
    )


    if result.empty:

        return result


    included_products = []


    for ingredient_name in (
        result["성분명"]
    ):

        products = []


        for _, drug in (
            drug_data.iterrows()
        ):

            if ingredient_name in (
                split_ingredients(
                    drug["성분"]
                )
            ):

                products.append(
                    drug["제품명"]
                )


        included_products.append(
            ", ".join(products)
            if products
            else "-"
        )


    result[
        "포함 제품"
    ] = included_products


    return result[
        [
            "성분명",
            "분류",
            "설명",
            "포함 제품",
        ]
    ]


# =========================================================
# 약 종류 필터
# =========================================================
def filter_drugs(
    drug_data,
    category,
):

    return drug_data[
        drug_data[
            "카테고리"
        ]
        == category
    ].copy()
