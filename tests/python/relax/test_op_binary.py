# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
import pytest
import tvm
import tvm.testing
from tvm import relax, tir
from tvm import TVMError
from tvm.ir import Op
from tvm.script import relax as R


def test_op_correctness():
    x = relax.Var("x", R.Tensor((2, 3), "float32"))
    y = relax.Var("y", R.Tensor((2, 3), "float32"))
    assert relax.op.add(x, y).op == Op.get("relax.add")
    assert relax.op.divide(x, y).op == Op.get("relax.divide")
    assert relax.op.floor_divide(x, y).op == Op.get("relax.floor_divide")
    assert relax.op.multiply(x, y).op == Op.get("relax.multiply")
    assert relax.op.subtract(x, y).op == Op.get("relax.subtract")

    assert relax.op.equal(x, y).op == Op.get("relax.equal")
    assert relax.op.greater(x, y).op == Op.get("relax.greater")
    assert relax.op.greater_equal(x, y).op == Op.get("relax.greater_equal")
    assert relax.op.less(x, y).op == Op.get("relax.less")
    assert relax.op.less_equal(x, y).op == Op.get("relax.less_equal")
    assert relax.op.not_equal(x, y).op == Op.get("relax.not_equal")


def _check_inference(bb: relax.BlockBuilder, call: relax.Call, expected_sinfo: relax.StructInfo):
    ret = bb.normalize(call)
    tvm.ir.assert_structural_equal(ret.struct_info, expected_sinfo)


def test_binary_arith_infer_struct_info():
    bb = relax.BlockBuilder()
    x0 = relax.Var("x", R.Tensor((2, 3), "float32"))
    x1 = relax.Var("x", R.Tensor((1, 3), "float32"))
    x2 = relax.Var("x", R.Tensor((3, 2, 3), "float32"))
    x3 = relax.Var("x", R.Tensor((3, 1, 3), "float32"))
    x4 = relax.Var("x", R.Tensor("float32", ndim=2))
    x5 = relax.Var("x", R.Tensor())
    y0 = relax.Var("y", R.Tensor((2, 3), "float32"))
    y1 = relax.Var("y", R.Tensor((4, 3, 2, 1), "float32"))
    y2 = relax.Var("y", R.Tensor("float32", ndim=2))
    y3 = relax.Var("y", R.Tensor("float32", ndim=-1))

    _check_inference(bb, relax.op.add(x0, y0), relax.TensorStructInfo((2, 3), "float32"))
    _check_inference(bb, relax.op.subtract(x1, y0), relax.TensorStructInfo((2, 3), "float32"))
    _check_inference(bb, relax.op.multiply(x1, y1), relax.TensorStructInfo((4, 3, 2, 3), "float32"))
    _check_inference(bb, relax.op.divide(x2, y2), relax.TensorStructInfo(dtype="float32", ndim=3))
    _check_inference(
        bb, relax.op.floor_divide(x3, y2), relax.TensorStructInfo(dtype="float32", ndim=3)
    )
    _check_inference(bb, relax.op.add(x4, y0), relax.TensorStructInfo(dtype="float32", ndim=2))
    _check_inference(bb, relax.op.add(x4, y1), relax.TensorStructInfo(dtype="float32", ndim=4))
    _check_inference(bb, relax.op.add(x4, y2), relax.TensorStructInfo(dtype="float32", ndim=2))
    _check_inference(bb, relax.op.add(x4, y3), relax.TensorStructInfo(dtype="float32", ndim=-1))
    _check_inference(bb, relax.op.add(x5, y0), relax.TensorStructInfo(dtype="", ndim=-1))


def test_binary_cmp_infer_struct_info():
    bb = relax.BlockBuilder()
    x = relax.Var("x", R.Tensor((2, 3), "float32"))
    y0 = relax.Var("y", R.Tensor((2, 3), "float32"))
    y1 = relax.Var("y", R.Tensor((2, 3), "int32"))
    _check_inference(bb, relax.op.equal(x, y0), relax.TensorStructInfo((2, 3), "bool"))
    _check_inference(bb, relax.op.greater(x, y1), relax.TensorStructInfo((2, 3), "bool"))
    _check_inference(bb, relax.op.greater_equal(x, y0), relax.TensorStructInfo((2, 3), "bool"))
    _check_inference(bb, relax.op.less(x, y1), relax.TensorStructInfo((2, 3), "bool"))
    _check_inference(bb, relax.op.less_equal(x, y0), relax.TensorStructInfo((2, 3), "bool"))
    _check_inference(bb, relax.op.not_equal(x, y1), relax.TensorStructInfo((2, 3), "bool"))


def test_binary_infer_struct_info_shape_symbolic():
    bb = relax.BlockBuilder()
    m = tir.Var("m", "int64")
    n = tir.Var("n", "int64")
    k = tir.Var("k", "int64")
    x0 = relax.Var("x", R.Tensor((m, n), "float32"))
    x1 = relax.Var("x", R.Tensor((1, n), "float32"))
    x2 = relax.Var("x", R.Tensor((k, n, m), "float32"))
    x3 = relax.Var("x", R.Tensor((3, 1, n), "float32"))
    x4 = relax.Var("x", R.Tensor("float32", ndim=2))
    y0 = relax.Var("y", R.Tensor((m, n), "float32"))
    y1 = relax.Var("y", R.Tensor((m, n + 2), "float32"))
    y2 = relax.Var("y", R.Tensor((4, k, m, 1), "float32"))
    y3 = relax.Var("y", R.Tensor("float32", ndim=2))
    y4 = relax.Var("y", R.Tensor("float32", ndim=-1))
    _check_inference(bb, relax.op.add(x0, y0), relax.TensorStructInfo((m, n), "float32"))
    _check_inference(bb, relax.op.add(x0, y1), relax.TensorStructInfo(dtype="float32", ndim=2))
    _check_inference(bb, relax.op.subtract(x1, y0), relax.TensorStructInfo((m, n), "float32"))
    _check_inference(bb, relax.op.multiply(x1, y2), relax.TensorStructInfo((4, k, m, n), "float32"))
    _check_inference(bb, relax.op.divide(x2, y2), relax.TensorStructInfo(dtype="float32", ndim=4))
    _check_inference(
        bb, relax.op.floor_divide(x2, y3), relax.TensorStructInfo(dtype="float32", ndim=3)
    )
    _check_inference(bb, relax.op.add(x3, y3), relax.TensorStructInfo(dtype="float32", ndim=3))
    _check_inference(bb, relax.op.add(x4, y0), relax.TensorStructInfo(dtype="float32", ndim=2))
    _check_inference(bb, relax.op.add(x4, y2), relax.TensorStructInfo(dtype="float32", ndim=4))
    _check_inference(bb, relax.op.add(x4, y3), relax.TensorStructInfo(dtype="float32", ndim=2))
    _check_inference(bb, relax.op.add(x4, y4), relax.TensorStructInfo(dtype="float32", ndim=-1))


def test_binary_infer_struct_info_shape_var():
    bb = relax.BlockBuilder()
    s0 = relax.Var("s0", relax.ShapeStructInfo(ndim=2))
    s1 = relax.Var("s1", relax.ShapeStructInfo(ndim=2))
    s2 = relax.Var("s2", relax.ShapeStructInfo(ndim=4))
    s3 = relax.Var("s3", relax.ShapeStructInfo(ndim=1))
    s4 = relax.Var("s4", relax.ShapeStructInfo())
    x = relax.Var("x", relax.TensorStructInfo(s0, "float32"))
    y0 = relax.Var("y", relax.TensorStructInfo(s0, "float32"))
    y1 = relax.Var("y", relax.TensorStructInfo(s1, "float32"))
    y2 = relax.Var("y", relax.TensorStructInfo(s2, "float32"))
    y3 = relax.Var("y", relax.TensorStructInfo(s3, "float32"))
    y4 = relax.Var("y", relax.TensorStructInfo(s4, "float32"))

    _check_inference(bb, relax.op.subtract(x, y0), relax.TensorStructInfo(s0, "float32"))
    _check_inference(bb, relax.op.subtract(x, y1), relax.TensorStructInfo(dtype="float32", ndim=2))
    _check_inference(bb, relax.op.subtract(x, y2), relax.TensorStructInfo(dtype="float32", ndim=4))
    _check_inference(bb, relax.op.subtract(x, y3), relax.TensorStructInfo(dtype="float32", ndim=2))
    _check_inference(bb, relax.op.subtract(x, y4), relax.TensorStructInfo(dtype="float32"))


def test_binary_arith_infer_struct_info_more_input_dtype():
    bb = relax.BlockBuilder()
    x0 = relax.Var("x", R.Tensor((2, 3), "float64"))
    y0 = relax.Var("y", R.Tensor((2, 3), "float64"))
    x1 = relax.Var("x", R.Tensor((2, 3), "int8"))
    y1 = relax.Var("y", R.Tensor((2, 3), "int8"))
    x2 = relax.Var("x", R.Tensor((2, 3), "int64"))
    y2 = relax.Var("y", R.Tensor((2, 3), "int64"))

    _check_inference(bb, relax.op.add(x0, y0), relax.TensorStructInfo((2, 3), "float64"))
    _check_inference(bb, relax.op.multiply(x1, y1), relax.TensorStructInfo((2, 3), "int8"))
    _check_inference(bb, relax.op.floor_divide(x2, y2), relax.TensorStructInfo((2, 3), "int64"))


def test_binary_infer_struct_info_shape_unequal_const_int():
    bb = relax.BlockBuilder()
    x0 = relax.Var("x", R.Tensor((2, 3), "float32"))
    y0 = relax.Var("y", R.Tensor((2, 4), "float32"))
    with pytest.raises(TVMError):
        bb.normalize(relax.op.add(x0, y0))


def test_binary_arith_infer_struct_info_dtype_mismatch():
    bb = relax.BlockBuilder()
    x = relax.Var("x", R.Tensor((2, 3), "float32"))
    y = relax.Var("y", R.Tensor((2, 3), "int32"))
    with pytest.raises(TVMError):
        bb.normalize(relax.op.add(x, y))


def test_binary_wrong_input_number():
    x = relax.Var("x", R.Tensor((2, 3), "float32"))

    with pytest.raises(TypeError):
        relax.op.subtract(x, x, x)
    with pytest.raises(TypeError):
        relax.op.less(x)
    with pytest.raises(TypeError):
        relax.op.divide(x, x, x, x)


def test_binary_infer_struct_info_wrong_input_type():
    bb = relax.BlockBuilder()
    x0 = relax.Var("x", relax.ShapeStructInfo((2, 3)))
    x1 = relax.Var("x", relax.FuncStructInfo([], R.Tensor((2, 3), "float32")))
    y = relax.Var("y", R.Tensor((2, 3), "float32"))

    with pytest.raises(TVMError):
        bb.normalize(relax.op.add(x0, y))
    with pytest.raises(TVMError):
        bb.normalize(relax.op.multiply(x1, y))


if __name__ == "__main__":
    tvm.testing.main()
