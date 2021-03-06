# -*- coding: utf-8 -*-
"""
Created on Thu Dec 19 18:33:31 2019

.dotauthor: shang
"""

from dsp_tool import __segment_axis
import numpy as np
import numba

from numba import complex128, double

from dsp_tool import decision

cma_core_type = (
    complex128[:, :], complex128[:, :], complex128[:, :], complex128[:, :], complex128[:, :], complex128[:, :], double)


def equalizer(signal, os, ntaps, mu, iter_number, method='cma', mode='training', training_time=1, train_symbol=None):
    ex = signal[0]
    ey = signal[1]

    ex = __segment_axis(ex, ntaps, ntaps - os)
    ey = __segment_axis(ey, ntaps, ntaps - os)
    wxx = np.zeros((1, ntaps), dtype=ex.dtype)
    wyy = np.zeros((1, ntaps), dtype=ex.dtype)
    wxy = np.zeros((1, ntaps), dtype=ex.dtype)
    wyx = np.zeros((1, ntaps), dtype=ex.dtype)

    wxy[0, ntaps // 2] = 1
    wyx[0, ntaps // 2] = 1
    error_xpol = []
    error_ypol = []

    if method == 'cma':
        for i in range(iter_number):
            wxx, wxy, wyx, wyy, error_x, error_y = cma_equalize_core(ex, ey, wxx, wyy, wxy, wyx, mu)
            error_xpol.append(error_x)
            error_ypol.append(error_y)
    elif method == 'lms':
        if mode == 'training':
            assert train_symbol is not None
            train_symbol = train_symbol[:, ntaps // 2 // os:]

            for i in range(iter_number):
                if training_time:
                    wxx, wxy, wyx, wyy, error_x, error_y = lms_equalize_core(ex, ey, wxx, wyy, wxy, wyx, mu, True,
                                                                             train_symbol[0], train_symbol[1],
                                                                             np.unique(train_symbol.flatten()))
                    training_time -= 1
                    error_xpol.append(error_x)
                    error_ypol.append(error_y)
                else:
                    wxx, wxy, wyx, wyy, error_x, error_y = lms_equalize_core(ex, ey, wxx, wyy, wxy, wyx, mu,
                                                                             training_time, train_symbol[0],
                                                                             train_symbol[1],
                                                                             np.unique(train_symbol.flatten()))
                    error_xpol.append(error_x)
                    error_ypol.append(error_y)
    else:
        raise NotImplementedError

    xout = ex[:, ::-1].dot(wxx.T) + ey[:, ::-1].dot(wxy.T)
    yout = ex[:, ::-1].dot(wyx.T) + ey[:, ::-1].dot(wyy.T)

    xout.shape = 1, -1
    yout.shape = 1, -1
    symbol = np.vstack((xout, yout))
    return symbol, (wxx, wxy, wyx, wyy, error_xpol, error_ypol)


@numba.njit(cache=True)
def lms_equalize_core(ex, ey, wxx, wyy, wxy, wyx, mu, is_train, train_symbol_xpol, train_symbol_ypol, constl):
    # symbols = np.zeros((1,ex.shape[0]),dtype=np.complex128)
    error_xpol_array = np.zeros((1, ex.shape[0]), dtype=np.float64)
    error_ypol_array = np.zeros((1, ey.shape[0]), dtype=np.float64)

    for idx in range(len(ex)):
        xx = ex[idx][::-1]
        yy = ey[idx][::-1]
        xout = np.sum(wxx * xx) + np.sum(wxy * yy)
        yout = np.sum(wyx * xx) + np.sum(wyy * yy)
        if is_train == 1:
            error_xpol = train_symbol_xpol[idx] - xout
            error_ypol = train_symbol_ypol[idx] - yout
        else:
            print(is_train)

            xpol_symbol = decision(xout, constl)
            ypol_symbol = decision(yout, constl)
            error_xpol = xout - xpol_symbol
            error_ypol = yout - ypol_symbol

        error_xpol_array[0, idx] = np.abs(error_xpol)
        error_ypol_array[0, idx] = np.abs(error_ypol)
        wxx = wxx + mu * error_xpol * np.conj(xx)
        wxy = wxy + mu * error_xpol * np.conj(yy)
        wyx = wyx + mu * error_ypol * np.conj(xx)
        wyy = wyy + mu * error_ypol * np.conj(yy)

    return wxx, wxy, wyx, wyy, error_xpol_array, error_ypol_array


@numba.njit(cma_core_type, cache=True)
def cma_equalize_core(ex, ey, wxx, wyy, wxy, wyx, mu):
    # symbols = np.zeros((1,ex.shape[0]),dtype=np.complex128)
    error_xpol_array = np.zeros((1, ex.shape[0]), dtype=np.float64)
    error_ypol_array = np.zeros((1, ex.shape[0]), dtype=np.float64)

    for idx in range(len(ex)):
        xx = ex[idx][::-1]
        yy = ey[idx][::-1]
        xout = np.sum(wxx * xx) + np.sum(wxy * yy)
        yout = np.sum(wyx * xx) + np.sum(wyy * yy)

        error_xpol = 1 - np.abs(xout) ** 2
        error_ypol = 1 - np.abs(yout) ** 2
        error_xpol_array[0, idx] = error_xpol
        error_xpol_array[0, idx] = error_ypol
        wxx = wxx + mu * error_xpol * xout * np.conj(xx)
        wxy = wxy + mu * error_xpol * xout * np.conj(yy)
        wyx = wyx + mu * error_ypol * yout * np.conj(xx)
        wyy = wyy + mu * error_ypol * yout * np.conj(yy)

    return wxx, wxy, wyx, wyy, error_xpol_array, error_ypol_array


def main():
    from scipy.io import loadmat
    from dsp import normalise_and_center
    # E = np.load('samples.npz')['samples'][:,1+300000:1+300000+200000]
    E = loadmat('toequ.mat')['tmp_rx']
    print(E.dtype)
    # E = normalise_and_center(E)
    symbol, _ = cma_equlizer(E, 2, 77, 0.0004, 2)
    from vis import scatterplot
    scatterplot(symbol[0])
    print('hello world')


if __name__ == '__main__':
    main()
